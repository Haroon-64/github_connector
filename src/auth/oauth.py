from authlib.integrations.starlette_client import OAuth

from src.core.config import settings
from src.core.constants import GITHUB_SCOPES

oauth = OAuth()

oauth.register(
    name="github",
    client_id=settings.OAUTH_CLIENT_ID,
    client_secret=settings.OAUTH_SECRET,
    access_token_url="https://github.com/login/oauth/access_token",
    access_token_params=None,
    authorize_url="https://github.com/login/oauth/authorize",
    authorize_params=None,
    api_base_url=settings.GITHUB_API_URL,
    client_kwargs={"scope": " ".join(GITHUB_SCOPES)},
)
