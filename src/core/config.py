from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    IP_ADDRESS: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "info"
    OAUTH_SECRET: str
    OAUTH_CLIENT_ID: str
    GITHUB_REDIRECT_URI: str
    GITHUB_API_URL: str = "https://api.github.com"
    CAMUNDA_URL: str = "http://localhost:8080/v2"

    # Camunda SaaS OAuth Credentials
    ZEEBE_CLIENT_ID: Optional[str] = None
    ZEEBE_CLIENT_SECRET: Optional[str] = None
    ZEEBE_AUTHORIZATION_SERVER_URL: Optional[str] = None
    ZEEBE_REST_ADDRESS: Optional[str] = None
    ZEEBE_TOKEN_AUDIENCE: Optional[str] = None

    model_config = SettingsConfigDict(extra="ignore", env_file=".env")


settings = Settings()  # type: ignore
