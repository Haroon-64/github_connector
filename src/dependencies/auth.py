import json

from fastapi import HTTPException, Request, status

from src.auth.oauth import oauth
from src.auth.service.github import GitHubAuthService


def get_auth_service() -> GitHubAuthService:
    """Dependency to provide GitHubAuthService instance."""
    return GitHubAuthService(oauth)


def get_current_user(request: Request):
    """Dependency to get the current authenticated user from cookie."""
    cookie_user = request.cookies.get("user_session")
    if not cookie_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        return json.loads(cookie_user)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session cookie",
        )
