from typing import Any, Callable, Dict, Optional

from fastapi import Depends, HTTPException, status

from src.dependencies.auth import get_optional_user
from src.github.client import GitHubClient
from src.github.service import GitHubService


def github_provider(required: bool = True) -> Callable[..., Any]:
    """
    Unified dependency provider for GitHub services.
    Handles both authenticated (required=True) and public (required=False) access.
    """

    def _get_github(
        user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    ) -> GitHubService:
        if required and not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required or session expired",
            )

        token = user["access_token"] if user else None
        return GitHubService(GitHubClient(token))

    return _get_github
