from typing import Any, Dict, List, Optional, cast

import structlog

from src.github.client import GitHubClient

logger = structlog.get_logger(__name__)


class GitHubService:
    """Service to handle high-level GitHub API operations."""

    def __init__(self, client: GitHubClient):
        self.client = client

    async def _request(
        self,
        method: str,
        endpoint: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **log_kwargs: Any,
    ) -> Any:
        """Centralized request helper with logging."""
        logger.debug(f"github_service_{operation}", endpoint=endpoint, **log_kwargs)
        return await self.client.request(
            method, endpoint, params=params, json_data=json_data
        )

    async def get_repositories(
        self, username: Optional[str] = None, org: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch repositories for a user, organization, or the current user."""
        if username:
            endpoint = f"/users/{username}/repos"
        elif org:
            endpoint = f"/orgs/{org}/repos"
        else:
            endpoint = "/user/repos"
        return cast(
            List[Dict[str, Any]],
            await self._request(
                "GET", endpoint, "get_repositories", username=username, org=org
            ),
        )

    async def get_user(self) -> Dict[str, Any]:
        """Fetch current user information."""
        return cast(
            Dict[str, Any], await self._request("GET", "/user", "get_current_user")
        )

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch single repository information."""
        return cast(
            Dict[str, Any],
            await self._request(
                "GET",
                f"/repos/{owner}/{repo}",
                "get_repository",
                owner=owner,
                repo=repo,
            ),
        )

    async def list_issues(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List issues for a repository."""
        return cast(
            List[Dict[str, Any]],
            await self._request(
                "GET",
                f"/repos/{owner}/{repo}/issues",
                "list_issues",
                owner=owner,
                repo=repo,
            ),
        )

    async def create_issue(
        self, owner: str, repo: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an issue in a repository."""
        return cast(
            Dict[str, Any],
            await self._request(
                "POST",
                f"/repos/{owner}/{repo}/issues",
                "create_issue",
                owner=owner,
                repo=repo,
                json_data=data,
            ),
        )

    async def create_pull_request(
        self, owner: str, repo: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a pull request in a repository."""
        return cast(
            Dict[str, Any],
            await self._request(
                "POST",
                f"/repos/{owner}/{repo}/pulls",
                "create_pull_request",
                owner=owner,
                repo=repo,
                json_data=data,
            ),
        )

    async def get_pulls(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        return cast(
            List[Dict[str, Any]],
            await self._request(
                "GET",
                f"/repos/{owner}/{repo}/pulls",
                "get_pulls",
                owner=owner,
                repo=repo,
            ),
        )

    async def get_commits(
        self, owner: str, repo: str, sha: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch commits from a repository, optionally filtered by SHA."""
        params = {"sha": sha} if sha else {}
        return cast(
            List[Dict[str, Any]],
            await self._request(
                "GET",
                f"/repos/{owner}/{repo}/commits",
                "get_commits",
                owner=owner,
                repo=repo,
                sha=sha,
                params=params,
            ),
        )

    async def create_pull_request_review(
        self, owner: str, repo: str, pull_number: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a review on a pull request."""
        return cast(
            Dict[str, Any],
            await self._request(
                "POST",
                f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
                "create_pull_request_review",
                owner=owner,
                repo=repo,
                pull_number=pull_number,
                json_data=data,
            ),
        )

    async def merge_pull_request(
        self, owner: str, repo: str, pull_number: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge a pull request."""
        return cast(
            Dict[str, Any],
            await self._request(
                "PUT",
                f"/repos/{owner}/{repo}/pulls/{pull_number}/merge",
                "merge_pull_request",
                owner=owner,
                repo=repo,
                pull_number=pull_number,
                json_data=data,
            ),
        )

    async def create_issue_comment(
        self, owner: str, repo: str, issue_number: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a comment on an issue or pull request."""
        return cast(
            Dict[str, Any],
            await self._request(
                "POST",
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                "create_issue_comment",
                owner=owner,
                repo=repo,
                issue_number=issue_number,
                json_data=data,
            ),
        )

