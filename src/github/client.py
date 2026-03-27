import asyncio
import re
import time
from typing import Any, Dict, List, Optional, cast

import httpx
import structlog

from src.core.config import settings
from src.models.error import (
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
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
        url = (
            endpoint
            if endpoint.startswith("http")
            else f"{self.base_url}/{endpoint.lstrip('/')}"
        )
        retry_count = 0

        while retry_count <= max_retries:
            logger.debug(
                "github_request_attempt", method=method, url=url, retry=retry_count
            )
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method, url, headers=self.headers, params=params, json=json_data
                    )
                    logger.info(
                        "github_request_completed", status_code=response.status_code
                    )
                    return await self._handle_response(
                        response,
                        method,
                        retry_count,
                        max_retries,
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
                if isinstance(
                    e,
                    (
                        AuthError,
                        ValidationError,
                        NotFoundError,
                        RateLimitError,
                        ServerError,
                        TimeoutError,
                        NetworkError,
                    ),
                ):
                    raise e
                raise ServerError()

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
        return await self._handle_error_response(response, retry_count, max_retries)

    async def _process_success(self, response: httpx.Response, method: str) -> Any:
        if method == "GET" and "Link" in response.headers:
            links = self._parse_link_header(response.headers["Link"])
            data = response.json()
            if isinstance(data, list) and "next" in links:
                next_data = await self._request("GET", links["next"])
                return data + next_data
            return data
        return response.json() if response.content else None

    async def _handle_error_response(
        self, response: httpx.Response, retry_count: int, max_retries: int
    ) -> Any:
        status = response.status_code
        if status in [401, 403] and "rate limit" not in response.text.lower():
            raise AuthError(status=status)
        if status == 404:
            raise NotFoundError()
        if status in [400, 422]:
            raise ValidationError(
                status=status, details=self._get_error_details(response)
            )
        if status in [403, 429]:
            return await self._handle_rate_limit(response, retry_count, max_retries)
        if status >= 500 and retry_count < max_retries:
            raise _RetryException(1.0 * (2**retry_count))
        raise ServerError()

    def _get_error_details(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except Exception:
            return response.text

    def _handle_rate_limit(
        self, response: httpx.Response, retry_count: int, max_retries: int
    ) -> Any:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            wait_time = float(retry_after)
        else:
            reset_time = response.headers.get("X-RateLimit-Reset")
            if reset_time:
                wait_time = max(0.01, float(reset_time) - time.time())
            else:
                wait_time = 1.0 * (2**retry_count)

        if retry_count < max_retries:
            raise _RetryException(wait_time)
        raise RateLimitError(retry_after=wait_time)

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
