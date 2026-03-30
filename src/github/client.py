import asyncio
import random
import re
import time
from typing import Any, Dict, List, Optional, cast

import httpx
import structlog

from src.core.config import settings
from src.github.retry_policy import GitHubRetryPolicy, RetryDecision, RetryType
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


class GitHubClient:
    def __init__(self, access_token: Optional[str] = None):
        self.base_url = settings.GITHUB_API_URL
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
        self.timeout = 10.0
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset: Optional[float] = None
        self.retry_policy = GitHubRetryPolicy(max_time=300.0)

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=self.headers)
        return self._client

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
        if self._rate_limit_remaining is None or self._rate_limit_reset is None:
            return

        wait_time = 0.0
        if self._rate_limit_remaining <= 0:
            wait_time = max(0.01, self._rate_limit_reset - time.time())
            wait_time += random.uniform(0, 1)
        elif self._rate_limit_remaining < 100:
            time_to_reset = max(0.01, self._rate_limit_reset - time.time())
            wait_time = time_to_reset / max(1, self._rate_limit_remaining)

        if wait_time > 0:
            logger.debug("github_request_pacing_or_throttle", wait=wait_time)
            await asyncio.sleep(wait_time)

    def _update_rate_limit_headers(self, response: httpx.Response) -> None:
        remaining = response.headers.get("x-ratelimit-remaining")
        reset = response.headers.get("x-ratelimit-reset")
        if remaining is not None:
            self._rate_limit_remaining = int(remaining)
        if reset is not None:
            self._rate_limit_reset = float(reset)

    async def _request(
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

    def _handle_network_exception(
        self,
        e: Exception,
        attempt_counts: Dict[RetryType, int],
    ) -> RetryDecision:
        return self.retry_policy.evaluate_exception(e, attempt_counts)

    def _finalize_response(self, response: httpx.Response, method: str) -> Any:
        status = response.status_code
        if status in (200, 201):
            return self._process_success_response(response, method)
        if status == 204:
            return None, None
        self._raise_for_status(response)

    def _check_stop_limits(
        self,
        decision: RetryDecision,
        attempt_counts: Dict[RetryType, int],
        start_time: float,
    ) -> None:
        if self.retry_policy.should_stop(decision, attempt_counts, start_time):
            if decision.retry_type == RetryType.RATE_LIMIT:
                raise RateLimitError()
            if decision.retry_type == RetryType.SERVER:
                raise ServerError()
            if decision.retry_type == RetryType.TIMEOUT:
                raise TimeoutError()
            raise NetworkError()

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
                decision = self._handle_network_exception(e, attempt_counts)

            if decision is None:
                return self._finalize_response(response, method)

            attempt_counts[decision.retry_type] += 1
            self._check_stop_limits(decision, attempt_counts, start_time)

            logger.warning(
                "github_request_retry",
                wait=decision.wait,
                retry_type=decision.retry_type.name,
                attempt=attempt_counts[decision.retry_type],
            )

            await asyncio.sleep(decision.wait)

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

    async def get_repositories(
        self, username: Optional[str] = None, org: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if username:
            endpoint = f"/users/{username}/repos"
        elif org:
            endpoint = f"/orgs/{org}/repos"
        else:
            endpoint = "/user/repos"
        return cast(List[Dict[str, Any]], await self._request("GET", endpoint))

    async def get_user(self) -> Dict[str, Any]:
        return cast(Dict[str, Any], await self._request("GET", "/user"))

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        return cast(
            Dict[str, Any],
            await self._request("GET", f"/repos/{owner}/{repo}"),
        )

    async def list_issues(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        return cast(
            List[Dict[str, Any]],
            await self._request("GET", f"/repos/{owner}/{repo}/issues"),
        )

    async def create_issue(
        self, owner: str, repo: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        return cast(
            Dict[str, Any],
            await self._request(
                "POST", f"/repos/{owner}/{repo}/issues", json_data=data
            ),
        )

    async def create_pull_request(
        self, owner: str, repo: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        return cast(
            Dict[str, Any],
            await self._request("POST", f"/repos/{owner}/{repo}/pulls", json_data=data),
        )

    async def get_commits(
        self, owner: str, repo: str, sha: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        params = {"sha": sha} if sha else {}
        return cast(
            List[Dict[str, Any]],
            await self._request("GET", f"/repos/{owner}/{repo}/commits", params=params),
        )
