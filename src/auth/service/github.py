from typing import Any, Dict

from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request


class GitHubAuthError(Exception):
    """Custom exception for GitHub Auth errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GitHubAuthService:
    """Service to handle GitHub OAuth logic."""

    def __init__(self, oauth: OAuth):
        self.oauth = oauth

    async def get_login_url(self, request: Request, redirect_uri: str) -> str:
        """Generate GitHub OAuth login URL."""
        try:
            response = await self.oauth.github.authorize_redirect(request, redirect_uri)
            return str(response.headers.get("Location", ""))
        except Exception as e:
            raise GitHubAuthError(f"Failed to generate login URL: {str(e)}")

    async def handle_callback(self, request: Request) -> Dict[str, Any]:
        """Handle GitHub OAuth callback and retrieve user info."""
        try:
            token = await self.oauth.github.authorize_access_token(request)
            user_info = await self.oauth.github.get("user", token=token)
            user_data = user_info.json()

            return {
                "access_token": token["access_token"],
                "token_type": token["token_type"],
                "username": user_data["login"],
                "user_data": user_data,
            }
        except Exception as e:
            raise GitHubAuthError(f"OAuth callback failed: {str(e)}")
