import json
import time
from typing import Any, Dict, Optional, cast

import structlog
from fastapi import Depends, HTTPException, Request, Response, status

from src.auth.oauth import oauth
from src.auth.service.github import GitHubAuthService

logger = structlog.get_logger(__name__)


def get_auth_service() -> GitHubAuthService:
    """Dependency to provide GitHubAuthService instance."""
    return GitHubAuthService(oauth)


async def _refresh_user_session(
    user_data: Dict[str, Any],
    auth_service: GitHubAuthService,
    response: Response,
) -> Optional[Dict[str, Any]]:
    """Internal helper to refresh an expired session."""
    refresh_token = user_data.get("refresh_token")
    if not refresh_token:
        logger.error("session_expired_no_refresh_token")
        return None

    try:
        new_token = await auth_service.refresh_access_token(refresh_token)
        # GitHub may or may not return a new refresh token
        user_data["access_token"] = new_token["access_token"]
        if new_token.get("refresh_token"):
            user_data["refresh_token"] = new_token["refresh_token"]

        created_at = new_token.get("created_at") or int(time.time())
        user_data["created_at"] = created_at

        if new_token.get("expires_in"):
            user_data["expires_at"] = created_at + new_token["expires_in"]
        else:
            user_data["expires_at"] = None

        logger.info("token_refreshed", username=user_data.get("username"))
        response.set_cookie(
            key="user_session",
            value=json.dumps(user_data),
            httponly=True,
            samesite="lax",
        )
        return user_data
    except Exception as e:
        logger.error("token_refresh_failed", error=str(e))
        return None


async def get_session_user(
    request: Request,
    response: Response,
    auth_service: GitHubAuthService = Depends(get_auth_service),
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
            logger.debug("session_expired_triggering_refresh")
            return await _refresh_user_session(user_data, auth_service, response)

        return cast(Dict[str, Any], user_data)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("session_parse_failed", error=str(e))
        return None


def get_current_user(
    user: Optional[Dict[str, Any]] = Depends(get_session_user),
) -> Dict[str, Any]:
    """Dependency to get current authenticated user, raises 401 if not found."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated or session expired",
        )
    return user
