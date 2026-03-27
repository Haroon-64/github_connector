import time
from typing import Any, Dict, cast

import structlog
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

logger = structlog.get_logger(__name__)


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
            login_url = str(response.headers.get("Location", ""))
            logger.info("login_url_generated", url=login_url)
            return login_url
        except Exception as e:
            raise GitHubAuthError(f"Failed to generate login URL: {str(e)}")

    async def handle_callback(self, request: Request) -> Dict[str, Any]:
        """Handle GitHub OAuth callback and retrieve user info."""
        try:
            token = await self.oauth.github.authorize_access_token(request)
            user_info = await self.oauth.github.get("user", token=token)
            user_data = user_info.json()
            logger.info("oauth_callback_success", username=user_data.get("login"))

            created_at = int(time.time())

            return {
                "access_token": token["access_token"],
                "token_type": token["token_type"],
                "username": user_data["login"],
                "user_data": user_data,
                "refresh_token": token.get("refresh_token"),
                "expires_in": token.get("expires_in"),
                "created_at": created_at,
            }
        except Exception as e:
            raise GitHubAuthError(f"OAuth callback failed: {str(e)}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh the GitHub access token using Authlib."""
        try:
            from src.core.config import settings

            # Using Authlib's client to refresh
            # GitHub's refresh token endpoint is the same as the token endpoint
            token_endpoint = "https://github.com/login/oauth/access_token"

            new_token = await self.oauth.github.fetch_access_token(
                url=token_endpoint,
                grant_type="refresh_token",
                refresh_token=refresh_token,
                client_id=settings.OAUTH_CLIENT_ID,
                client_secret=settings.OAUTH_SECRET,
            )
            logger.info("token_refreshed_successfully")

            new_token["created_at"] = int(time.time())
            return cast(Dict[str, Any], new_token)
        except Exception as e:
            raise GitHubAuthError(f"Failed to refresh token via Authlib: {str(e)}")

    async def revoke_token(self, access_token: str) -> None:
        """Revoke the GitHub access token."""
        try:
            import httpx

            from src.core.config import settings

            url = (
                f"https://api.github.com/applications/{settings.OAUTH_CLIENT_ID}/token"
            )
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    "DELETE",
                    url,
                    auth=(settings.OAUTH_CLIENT_ID, settings.OAUTH_SECRET),
                    json={"access_token": access_token},
                )
                if response.status_code not in [204, 404]:
                    logger.warning(
                        "token_revocation_failed", status_code=response.status_code
                    )
                else:
                    logger.info("token_revoked_successfully")
        except Exception as e:
            logger.error("token_revocation_error", error=str(e))
            # Silence revocation errors during logout to ensure session is cleared
            pass
