import re
from typing import Any, Dict, Optional

import httpx
import structlog

from src.core.config import settings
from src.github.retry_policy import GitHubRetryPolicy
from src.models.error import (
    AuthError,
    ConflictError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    RedirectError,
    ServerError,
    ValidationError,
)

logger = structlog.get_logger(__name__)


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

    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
    ) -> httpx.Response:
        """
        Execute a single HTTP request without retry logic.
        """
        return await self.client.request(method, url, params=params, json=json_data)

    async def _fetch_page_with_retries(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
    ) -> Any:
        async def request_callback() -> httpx.Response:
            return await self._make_request(method, url, params, json_data)

        response = await self.retry_policy.execute_with_retries(
            request_callback, self._access_token
        )

        return self._finalize_response(response, method)

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
