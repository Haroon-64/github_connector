from functools import lru_cache
from typing import Any, Callable, Dict, Optional

import structlog
from fastapi import HTTPException, Request, status

from src.auth.oauth import oauth
from src.auth.service import GitHubAuthService
from src.core.session import SESSION_CACHE, TOKEN_CACHE
from src.github.client import GitHubClient

logger = structlog.get_logger(__name__)


def get_auth_service() -> GitHubAuthService:
    """Dependency to provide GitHubAuthService instance."""
    return GitHubAuthService(oauth)


@lru_cache()
def auth_provider(required: bool = True) -> Callable[..., Any]:
    """
    Unified dependency provider for authentication.
    Handles both session cookies and Bearer tokens.
    """

    async def _get_user_from_bearer(token: str) -> Optional[Dict[str, Any]]:
        if token in TOKEN_CACHE:
            return {"access_token": token, "username": TOKEN_CACHE[token]}

        try:
            client = GitHubClient(token)
            user_data = await client.request("GET", "user")
            await client.aclose()

            username = user_data["login"]
            TOKEN_CACHE[token] = username
            return {"access_token": token, "username": username}
        except Exception as e:
            logger.warning("bearer_token_validation_failed", error=str(e))
            if required:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid bearer token",
                )
            return None

    async def _get_user(request: Request) -> Optional[Dict[str, Any]]:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return await _get_user_from_bearer(
                auth_header.replace("Bearer ", "").strip()
            )

        session_id = request.cookies.get("user_session")
        user = SESSION_CACHE.get(session_id) if session_id else None

        if required and not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated or session expired",
            )
        return user

    return _get_user
