import asyncio
import random
import re
import time
from typing import Any, Dict, Optional

import httpx
import structlog

from src.core.config import settings
from src.github.retry_policy import GitHubRetryPolicy, RetryType
from src.models.error import (
    AuthError,
    ConflictError,
    NetworkError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    RedirectError,
    ServerError,
    TimeoutError,
    ValidationError,
)

logger = structlog.get_logger(__name__)

# Keyed by access_token (or None for unauthenticated).
# Stores: {"remaining": int, "reset": float}
RATE_LIMIT_STATE: Dict[Optional[str], Dict[str, Any]] = {}


class GitHubClient:
    def __init__(self, access_token: Optional[str] = None):
        self._access_token = access_token
        self.base_url = settings.GITHUB_API_URL
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
        self.timeout = 10.0
        self._client: Optional[httpx.AsyncClient] = None
        self.retry_policy = GitHubRetryPolicy(max_time=300.0)

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=self.headers)
        return self._client

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url: Optional[str] = f"{self.base_url}/{endpoint.lstrip('/')}"
        all_data = None

        while url:
            page_data, next_url = await self._fetch_page_with_retries(
                method, url, params, json_data
            )

            if all_data is None:
                all_data = page_data
            elif isinstance(all_data, list) and isinstance(page_data, list):
                all_data.extend(page_data)

            url = next_url
            params = None

        return all_data

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _parse_link_header(self, header: str) -> Dict[str, str]:
        links: Dict[str, str] = {}
        if not header:
            return links
        parts = header.split(",")
        for part in parts:
            match = re.search(r'<(.*)>; rel="(.*)"', part.strip())
            if match:
                url, rel = match.groups()
                links[rel] = url
        return links

    def _get_error_details(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except Exception:
            logger.error("failed_to_parse_error_response", response=response.text)
            return response.text

    async def _throttle_and_pace(self) -> None:
        """Proactively delays requests based on stored rate limit state (pacing).

        This is different from the retry policy, which reactively handles
        rate limit errors (403/429) after they occur.
        """
        state = RATE_LIMIT_STATE.get(self._access_token)
        if not state:
            return

        remaining = state.get("remaining")
        reset = state.get("reset")
        if remaining is None or reset is None:
            return

        wait_time = 0.0
        if remaining <= 0:
            wait_time = max(0.01, reset - time.time())
            wait_time += random.uniform(0, 1)
        elif remaining < 100:
            time_to_reset = max(0.01, reset - time.time())
            wait_time = time_to_reset / max(1, remaining)

        if wait_time > 0:
            # Short-circuit if wait is too long
            if wait_time > 600:
                logger.warning("pacing_wait_too_long", wait=wait_time)
                raise RateLimitError()

            logger.debug("github_request_pacing_or_throttle", wait=wait_time)
            await asyncio.sleep(wait_time)

    def _update_rate_limit_headers(self, response: httpx.Response) -> None:
        remaining = response.headers.get("x-ratelimit-remaining")
        reset = response.headers.get("x-ratelimit-reset")
        if remaining is not None or reset is not None:
            state = RATE_LIMIT_STATE.get(self._access_token, {})
            if remaining is not None:
                state["remaining"] = int(remaining)
            if reset is not None:
                state["reset"] = float(reset)
            RATE_LIMIT_STATE[self._access_token] = state

    async def _fetch_page_with_retries(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
    ) -> Any:
        start_time = time.time()
        attempt_counts = {
            RetryType.RATE_LIMIT: 0,
            RetryType.SERVER: 0,
            RetryType.NETWORK: 0,
            RetryType.TIMEOUT: 0,
        }

        while True:
            await self._throttle_and_pace()

            try:
                response = await self.client.request(
                    method, url, params=params, json=json_data
                )
                self._update_rate_limit_headers(response)
                decision = self.retry_policy.evaluate_response(response, attempt_counts)

            except (httpx.TimeoutException, httpx.RequestError) as e:
                decision = self.retry_policy.evaluate_exception(e, attempt_counts)

            if decision is None:
                return self._finalize_response(response, method)

            attempt_counts[decision.retry_type] += 1
            if self.retry_policy.should_stop(decision, attempt_counts, start_time):
                self._handle_retry_failure(decision)

            logger.warning(
                "github_request_retry",
                wait=decision.wait,
                retry_type=decision.retry_type.name,
                attempt=attempt_counts[decision.retry_type],
            )
            await asyncio.sleep(decision.wait)

    def _handle_retry_failure(self, decision: Any) -> None:
        """Raises the appropriate exception when retry limits are hit."""
        if decision.retry_type == RetryType.RATE_LIMIT:
            raise RateLimitError()
        if decision.retry_type == RetryType.SERVER:
            raise ServerError()
        if decision.retry_type == RetryType.TIMEOUT:
            raise TimeoutError()
        raise NetworkError()

    def _finalize_response(self, response: httpx.Response, method: str) -> Any:
        status = response.status_code
        if status in (200, 201):
            return self._process_success_response(response, method)
        if status == 204:
            return None, None
        self._raise_for_status(response)

    def _process_success_response(self, response: httpx.Response, method: str) -> Any:
        page_data = response.json() if response.content else None
        next_url = None
        if method == "GET" and isinstance(page_data, list):
            next_url = self._extract_next_url(response.headers)
        return page_data, next_url

    def _extract_next_url(self, headers: httpx.Headers) -> Optional[str]:
        if "Link" in headers:
            links = self._parse_link_header(headers["Link"])
            if "next" in links:
                url = links["next"]
                if not url.startswith(self.base_url):
                    url = f"{self.base_url}/{url.lstrip('/')}"
                return url
        return None

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        if status == 401:
            raise AuthError(status=401)
        if status == 403:
            raise PermissionError(status=403)
        if status == 404:
            raise NotFoundError()
        if status == 301:
            raise RedirectError()
        if status == 409:
            raise ConflictError()
        if status == 429:
            raise RateLimitError()
        if status in [400, 422]:
            raise ValidationError(
                status=status, details=self._get_error_details(response)
            )
        raise ServerError()
