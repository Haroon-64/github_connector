import time
from typing import Optional

import httpx
import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)

_token_cache: Optional[str] = None
_token_expiry: float = 0


async def get_camunda_token() -> Optional[str]:
    """
    Fetches an OAuth JWT from Camunda SaaS using client credentials.
    Returns None if ZEEBE_CLIENT_ID is not configured (e.g., local dev).
    """
    if not settings.ZEEBE_CLIENT_ID:
        return None

    global _token_cache, _token_expiry
    current_time = time.time()

    if _token_cache and current_time < _token_expiry - 60:
        return _token_cache

    logger.debug("fetching_new_camunda_saas_token")
    url = (
        settings.ZEEBE_AUTHORIZATION_SERVER_URL
        or "https://login.cloud.camunda.io/oauth/token"
    )

    payload = {
        "grant_type": "client_credentials",
        "audience": settings.ZEEBE_TOKEN_AUDIENCE or "zeebe.camunda.io",
        "client_id": settings.ZEEBE_CLIENT_ID,
        "client_secret": settings.ZEEBE_CLIENT_SECRET,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload)
            response.raise_for_status()
            data = response.json()

            _token_cache = data.get("access_token")
            _token_expiry = current_time + data.get("expires_in", 3600)

            logger.info("camunda_saas_token_acquired")
            return _token_cache
    except Exception as e:
        logger.error("failed_to_fetch_camunda_saas_token", error=str(e))
        raise
