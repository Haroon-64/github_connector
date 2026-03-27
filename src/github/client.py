import asyncio
import re
import time
from typing import Any, Dict, List, Optional, cast

import httpx
import structlog

from src.core.config import settings
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


class _RetryException(Exception):
    def __init__(self, wait_time: float):
        self.wait_time = wait_time


class GitHubClient:
    def __init__(self, access_token: str):
        self.base_url = settings.GITHUB_API_URL
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.timeout = 10.0

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

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retry_count = 0

        while retry_count <= max_retries:
            logger.debug(
                "github_request_attempt", method=method, url=url, retry=retry_count
            )
            try:
                return await self._execute_request_attempt(
                    method, url, params, json_data, retry_count, max_retries
                )
            except _RetryException as e:
                logger.warning("github_request_retry", wait=e.wait_time)
                retry_count += 1
                await asyncio.sleep(e.wait_time)
                continue
            except httpx.TimeoutException:
                if retry_count < max_retries:
                    retry_count += 1
                    continue
                raise TimeoutError()
            except httpx.RequestError:
                raise NetworkError()
            except Exception as e:
                self._raise_if_api_error(e)

    def _raise_if_api_error(self, e: Exception) -> None:
        if isinstance(
            e,
            (
                AuthError,
                PermissionError,
                ValidationError,
                NotFoundError,
                RateLimitError,
                RedirectError,
                ConflictError,
                ServerError,
                TimeoutError,
                NetworkError,
            ),
        ):
            raise e
        raise ServerError()

    async def _proactive_throttle(self, response: httpx.Response) -> None:
        """Throttles proactively if remaining rate limit hits zero."""
        remaining = response.headers.get("x-ratelimit-remaining")
        if remaining and int(remaining) == 0:
            reset = response.headers.get("x-ratelimit-reset")
            if reset:
                wait_time = max(0.01, float(reset) - time.time())
                logger.warning("proactive_throttle_sleep", wait=wait_time)
                await asyncio.sleep(wait_time)

    async def _handle_response(
        self,
        response: httpx.Response,
        method: str,
        retry_count: int,
        max_retries: int,
    ) -> Any:
        if response.status_code in [200, 201]:
            return await self._process_success(response, method)
        if response.status_code == 204:
            return None
        return self._handle_error_response(response, retry_count, max_retries)

    async def _process_success(self, response: httpx.Response, method: str) -> Any:
        if method == "GET" and "Link" in response.headers:
            links = self._parse_link_header(response.headers["Link"])
            data = response.json()
            if isinstance(data, list) and "next" in links:
                next_url = links["next"]
                if next_url.startswith(self.base_url):
                    next_url = next_url[len(self.base_url) :]
                next_data = await self._request("GET", next_url)
                return data + next_data
            return data
        return response.json() if response.content else None

    def _handle_error_response(
        self, response: httpx.Response, retry_count: int, max_retries: int
    ) -> Any:
        status = response.status_code
        if status == 401:
            raise AuthError(status=401)
        if status == 403:
            return self._handle_403_error(response, retry_count, max_retries)
        if status == 404:
            raise NotFoundError()
        if status == 301:
            raise RedirectError()
        if status == 409:
            raise ConflictError()
        if status in [400, 422]:
            raise ValidationError(
                status=status, details=self._get_error_details(response)
            )
        if status == 429:
            return self._handle_429_error(response, retry_count, max_retries)
        if status >= 500 and retry_count < max_retries:
            raise _RetryException(1.0 * (2**retry_count))
        raise ServerError()

    def _handle_403_error(
        self, response: httpx.Response, retry_count: int, max_retries: int
    ) -> Any:
        headers = response.headers
        body = response.text.lower()

        if "retry-after" in headers:
            return self._handle_rate_limit_retry_after(
                headers["retry-after"], retry_count, max_retries
            )

        if headers.get("x-ratelimit-remaining") == "0":
            return self._handle_rate_limit_reset(
                headers.get("x-ratelimit-reset"), retry_count, max_retries
            )

        if "rate limit" in body or "secondary rate limit" in body:
            return self._handle_rate_limit_backoff(retry_count, max_retries)

        raise PermissionError(status=403)

    def _handle_429_error(
        self, response: httpx.Response, retry_count: int, max_retries: int
    ) -> Any:
        headers = response.headers
        if "retry-after" in headers:
            return self._handle_rate_limit_retry_after(
                headers["retry-after"], retry_count, max_retries
            )
        return self._handle_rate_limit_backoff(retry_count, max_retries)

    async def _execute_request_attempt(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
        retry_count: int,
        max_retries: int,
    ) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method, url, headers=self.headers, params=params, json=json_data
            )
        logger.info("github_request_completed", status_code=response.status_code)
        await self._proactive_throttle(response)
        return await self._handle_response(response, method, retry_count, max_retries)

    def _get_error_details(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except Exception:
            return response.text

    def _trigger_retry(
        self, wait_seconds: float, retry_count: int, max_retries: int
    ) -> Any:
        if retry_count < max_retries:
            raise _RetryException(wait_seconds)
        raise RateLimitError(retry_after=wait_seconds)

    def _handle_rate_limit_retry_after(
        self, retry_after: str, retry_count: int, max_retries: int
    ) -> Any:
        wait_seconds = float(retry_after)
        return self._trigger_retry(wait_seconds, retry_count, max_retries)

    def _handle_rate_limit_reset(
        self, reset: Optional[str], retry_count: int, max_retries: int
    ) -> Any:
        if reset:
            wait_seconds = max(0.01, float(reset) - time.time())
        else:
            wait_seconds = 1.0 * (2**retry_count)
        return self._trigger_retry(wait_seconds, retry_count, max_retries)

    def _handle_rate_limit_backoff(self, retry_count: int, max_retries: int) -> Any:
        wait_seconds = 1.0 * (2**retry_count)
        return self._trigger_retry(wait_seconds, retry_count, max_retries)

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
        response_data = await self._request(
            "POST", f"/repos/{owner}/{repo}/pulls", json_data=data
        )
        return cast(Dict[str, Any], response_data)

    async def get_commits(
        self, owner: str, repo: str, sha: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        params = {"sha": sha} if sha else {}
        return cast(
            List[Dict[str, Any]],
            await self._request("GET", f"/repos/{owner}/{repo}/commits", params=params),
        )
