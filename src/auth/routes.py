import secrets
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.auth.service import GitHubAuthError, GitHubAuthService
from src.core.config import settings
from src.core.constants import GITHUB_SCOPES
from src.core.session import SESSION_CACHE
from src.dependencies.auth import (
    get_auth_service,
    get_current_user,
    get_session_user,
)
from src.models.auth import CallbackResponse, LoginResponse, UserResponse

auth_router = APIRouter()


@auth_router.get("/github/login", response_model=LoginResponse)
async def github_login(
    request: Request,
    scope: Optional[str] = Query(
        " ".join(GITHUB_SCOPES),
        description=(
            "A space-delimited list of scopes. "
            f"Allowed scopes: {', '.join(GITHUB_SCOPES)}"
        ),
    ),
    auth_service: GitHubAuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Initiate GitHub OAuth login flow."""
    try:
        login_url = await auth_service.get_login_url(
            request,
            redirect_uri=settings.GITHUB_REDIRECT_URI,
            scope=scope,
        )
        return LoginResponse(login_url=login_url)
    except GitHubAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.get(
    "/github/callback", response_model=CallbackResponse, include_in_schema=False
)
async def github_callback(
    request: Request,
    response: Response,
    auth_service: GitHubAuthService = Depends(get_auth_service),
) -> CallbackResponse:
    """Handle GitHub OAuth callback and retrieve access token."""
    try:
        result = await auth_service.handle_callback(request)

        # Store user in an HTTP-only cookie
        user_data = {
            "username": result["username"],
            "access_token": result["access_token"],
            "created_at": result["created_at"],
        }

        session_id = secrets.token_urlsafe(32)
        SESSION_CACHE[session_id] = user_data

        response.set_cookie(
            key="user_session",
            value=session_id,
            httponly=True,
            samesite="lax",
            secure=True,
        )

        return CallbackResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            username=result["username"],
            created_at=result["created_at"],
        )
    except GitHubAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: Optional[dict[str, Any]] = Depends(get_session_user),
    auth_service: GitHubAuthService = Depends(get_auth_service),
) -> Any:
    """Log out the user by clearing the session cookie and revoking the token."""
    if user and user.get("access_token"):
        await auth_service.revoke_token(user["access_token"])

    session_id = request.cookies.get("user_session")
    if session_id and session_id in SESSION_CACHE:
        del SESSION_CACHE[session_id]

    response.delete_cookie(key="user_session")
    return {"message": "Logged out successfully"}


@auth_router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserResponse:
    """Get currently authenticated user info."""
    return UserResponse(**current_user)
