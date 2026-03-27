import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.auth.service.github import GitHubAuthError, GitHubAuthService
from src.core.config import settings
from src.dependencies.auth import get_auth_service, get_current_user
from src.models.auth import CallbackResponse, LoginResponse

auth_router = APIRouter()


@auth_router.get("/github/login", response_model=LoginResponse)
async def github_login(
    request: Request,
    auth_service: GitHubAuthService = Depends(get_auth_service),
):
    """Initiate GitHub OAuth login flow."""
    try:
        login_url = await auth_service.get_login_url(
            request, settings.GITHUB_REDIRECT_URI
        )
        return LoginResponse(login_url=login_url)
    except GitHubAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.get("/github/callback", response_model=CallbackResponse)
async def github_callback(
    request: Request,
    response: Response,
    auth_service: GitHubAuthService = Depends(get_auth_service),
):
    """Handle GitHub OAuth callback and retrieve access token."""
    try:
        result = await auth_service.handle_callback(request)

        # Store user in an HTTP-only cookie for now,
        # later should be moved to encrypted DB+redis
        user_data = {
            "username": result["username"],
            "access_token": result["access_token"],
        }
        response.set_cookie(
            key="user_session",
            value=json.dumps(user_data),
            httponly=True,
            samesite="lax",
        )

        return CallbackResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            username=result["username"],
        )
    except GitHubAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@auth_router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get currently authenticated user info."""
    return current_user
