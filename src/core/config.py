from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    IP_ADDRESS: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "info"
    OAUTH_SECRET: str
    OAUTH_CLIENT_ID: str
    GITHUB_REDIRECT_URI: str
    GITHUB_API_URL: str = "https://api.github.com"

    model_config = {"env_file": ".env"}


settings = Settings()  # type: ignore
