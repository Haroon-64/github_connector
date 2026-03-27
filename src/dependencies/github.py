from typing import Any

from fastapi import Depends

from src.dependencies.auth import get_current_user
from src.github.client import GitHubClient


def get_github_client(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> GitHubClient:
    """Dependency to provide a GitHubClient instance,
    for the current authenticated user."""
    return GitHubClient(current_user["access_token"])
