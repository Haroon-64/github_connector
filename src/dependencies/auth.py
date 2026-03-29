import json
import time
from typing import Any, Dict, Optional, cast

import structlog
from fastapi import Depends, HTTPException, Request, status

from src.auth.oauth import oauth
from src.auth.service.github import GitHubAuthService

logger = structlog.get_logger(__name__)


def get_auth_service() -> GitHubAuthService:
    """Dependency to provide GitHubAuthService instance."""
    return GitHubAuthService(oauth)


def get_session_user(
    request: Request,
) -> Optional[Dict[str, Any]]:
    """Dependency to get user from session cookie, handling refresh if needed."""
    cookie_user = request.cookies.get("user_session")
    if not cookie_user:
        return None

    try:
        user_data = json.loads(cookie_user)
        # Check for expiration
        expires_at = user_data.get("expires_at")
        if expires_at and time.time() > expires_at:
            logger.debug("session_expired")
            return None

        return cast(Dict[str, Any], user_data)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("session_parse_failed", error=str(e))
        return None


def get_optional_user(
    request: Request,
    user: Optional[Dict[str, Any]] = Depends(get_session_user),
) -> Optional[Dict[str, Any]]:
    """Dependency to get current authenticated user, returns None if not found."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        return {"access_token": token, "username": "api_user"}

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
