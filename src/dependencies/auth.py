from typing import Any, Dict, Optional, cast

import structlog
from fastapi import Depends, HTTPException, Request, status

from src.auth.oauth import oauth
from src.auth.service.github import GitHubAuthService
from src.core.session import SESSION_CACHE, TOKEN_CACHE
from src.github.client import GitHubClient

logger = structlog.get_logger(__name__)


def get_auth_service() -> GitHubAuthService:
    """Dependency to provide GitHubAuthService instance."""
    return GitHubAuthService(oauth)


def get_session_user(
    request: Request,
) -> Optional[Dict[str, Any]]:
    """Dependency to get user from session cookie."""
    session_id = request.cookies.get("user_session")
    if not session_id:
        return None

    return SESSION_CACHE.get(session_id)


async def get_optional_user(
    request: Request,
    user: Optional[Dict[str, Any]] = Depends(get_session_user),
) -> Optional[Dict[str, Any]]:
    """Dependency to get current authenticated user, returns None if not found."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()

        if token in TOKEN_CACHE:
            return {"access_token": token, "username": TOKEN_CACHE[token]}

        try:
            client = GitHubClient(token)
            user_data = await client.get_user()
            await client.aclose()

            username = user_data["login"]
            TOKEN_CACHE[token] = username
            return {"access_token": token, "username": username}
        except Exception as e:
            logger.warning("bearer_token_validation_failed", error=str(e))
            return None

    return user


def get_current_user(
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Dependency to get current authenticated user, raises 401 if not found."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated or session expired",
        )
    return user
