import time
from typing import Any, Dict, Optional

import httpx
import structlog
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from src.core.config import settings

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

    async def get_login_url(
        self,
        request: Request,
        redirect_uri: str,
        scope: Optional[str] = None,
    ) -> str:
        """Generate GitHub OAuth login URL."""
        logger.debug("generating_login_url", scope=scope)
        try:
            kwargs: Dict[str, Any] = {}
            if scope:
                kwargs["scope"] = scope

            response = await self.oauth.github.authorize_redirect(
                request, redirect_uri, **kwargs
            )
            login_url = str(response.headers.get("Location", ""))
            logger.info("login_url_generated", url=login_url)
            return login_url
        except Exception as e:
            raise GitHubAuthError(f"Failed to generate login URL: {str(e)}")

    async def handle_callback(self, request: Request) -> Dict[str, Any]:
        """Handle GitHub OAuth callback and retrieve user info."""
        logger.debug("handling_oauth_callback")
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
                "created_at": created_at,
            }
        except Exception as e:
            raise GitHubAuthError(f"OAuth callback failed: {str(e)}")

    async def revoke_token(self, access_token: str) -> None:
        """Revoke the GitHub access token."""
        logger.debug("revoking_token")
        try:
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
                if response.status_code == 429:
                    logger.warning(
                        "token_revocation_rate_limited",
                        detail="Proceeding with logout anyway",
                    )
                elif response.status_code not in [204, 404]:
                    logger.warning(
                        "token_revocation_failed", status_code=response.status_code
                    )
                else:
                    logger.info("token_revoked_successfully")
        except Exception as e:
            logger.error("token_revocation_error", error=str(e))
