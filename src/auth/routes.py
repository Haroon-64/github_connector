from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from src.auth.service import GitHubAuthError, GitHubAuthService
from src.core.config import settings
from src.core.constants import GITHUB_SCOPES
from src.dependencies.auth import (
    auth_provider,
    get_auth_service,
)
from src.models.auth import UserResponse

auth_router = APIRouter()
logger = structlog.get_logger(__name__)


@auth_router.get("/github/login", include_in_schema=False)
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
) -> RedirectResponse:
    """Initiate GitHub OAuth login flow."""
    logger.debug("github_login_start", scope=scope)
    try:
        login_url = await auth_service.get_login_url(
            request,
            redirect_uri=settings.GITHUB_REDIRECT_URI,
            scope=scope,
        )
        return RedirectResponse(url=login_url)
    except GitHubAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.get("/github/callback", include_in_schema=False)
async def github_callback(
    request: Request,
    auth_service: GitHubAuthService = Depends(get_auth_service),
) -> Any:
    """Handle GitHub OAuth callback and retrieve access token."""
    logger.debug("github_callback_received")
    try:
        result = await auth_service.handle_callback(request)

        redirect_response = RedirectResponse(url="/")

        # Store user in an HTTP-only cookie using the service layer
        auth_service.login_user(redirect_response, result)

        return redirect_response
    except GitHubAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: Optional[Dict[str, Any]] = Depends(auth_provider(required=False)),
    auth_service: GitHubAuthService = Depends(get_auth_service),
) -> Any:
    """Log out the user by clearing the session cookie and revoking the token."""
    session_id = request.cookies.get("user_session")
    await auth_service.logout_user(
        response=response,
        session_id=session_id,
        access_token=user.get("access_token") if user else None,
    )

    return {"message": "Logged out successfully"}


@auth_router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Dict[str, Any] = Depends(auth_provider(required=True)),
) -> UserResponse:
    """Get currently authenticated user info."""
    logger.debug("get_me_requested", username=current_user.get("username"))
    return UserResponse(**current_user)
