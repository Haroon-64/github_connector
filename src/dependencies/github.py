from typing import Any, Optional

from fastapi import Depends

from src.dependencies.auth import get_current_user, get_optional_user
from src.github.client import GitHubClient
from src.github.service import GitHubService


def get_github_client(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> GitHubClient:
    """Dependency to provide a GitHubClient
    instance for the current authenticated user."""
    return GitHubClient(current_user["access_token"])


def get_optional_github_client(
    current_user: Optional[dict[str, Any]] = Depends(get_optional_user),
) -> GitHubClient:
    """Dependency to provide a GitHubClient instance, optionally authenticated."""
    token = current_user["access_token"] if current_user else None
    return GitHubClient(token)


def get_github_service(
    client: GitHubClient = Depends(get_github_client),
) -> GitHubService:
    """Dependency to provide a GitHubService instance."""
    return GitHubService(client)


def get_optional_github_service(
    client: GitHubClient = Depends(get_optional_github_client),
) -> GitHubService:
    """Dependency to provide a GitHubService instance, optionally authenticated."""
    return GitHubService(client)
