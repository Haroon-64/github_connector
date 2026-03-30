from typing import Any, Dict, List, Optional, cast

from src.github.client import GitHubClient


class GitHubService:
    """Service to handle high-level GitHub API operations."""

    def __init__(self, client: GitHubClient):
        self.client = client

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
        return cast(List[Dict[str, Any]], await self.client.request("GET", endpoint))

    async def get_user(self) -> Dict[str, Any]:
        """Fetch current user information."""
        return cast(Dict[str, Any], await self.client.request("GET", "/user"))

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch single repository information."""
        return cast(
            Dict[str, Any],
            await self.client.request("GET", f"/repos/{owner}/{repo}"),
        )

    async def list_issues(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List issues for a repository."""
        return cast(
            List[Dict[str, Any]],
            await self.client.request("GET", f"/repos/{owner}/{repo}/issues"),
        )

    async def create_issue(
        self, owner: str, repo: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an issue in a repository."""
        return cast(
            Dict[str, Any],
            await self.client.request(
                "POST", f"/repos/{owner}/{repo}/issues", json_data=data
            ),
        )

    async def create_pull_request(
        self, owner: str, repo: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a pull request in a repository."""
        return cast(
            Dict[str, Any],
            await self.client.request(
                "POST", f"/repos/{owner}/{repo}/pulls", json_data=data
            ),
        )

    async def get_commits(
        self, owner: str, repo: str, sha: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch commits from a repository, optionally filtered by SHA."""
        params = {"sha": sha} if sha else {}
        return cast(
            List[Dict[str, Any]],
            await self.client.request(
                "GET", f"/repos/{owner}/{repo}/commits", params=params
            ),
        )
