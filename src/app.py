import uvicorn
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from src.auth.routes import auth_router
from src.core.config import settings
from src.core.logging import setup_logging
from src.github.routes import github_router

logger = setup_logging()


app = FastAPI(
    title="GitHub Connector",
    version="1.0.0",
    description="FastAPI-based GitHub Connector",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(SessionMiddleware, secret_key=settings.OAUTH_SECRET)
app.include_router(auth_router, prefix="/auth")
app.include_router(github_router, prefix="/github")


if __name__ == "__main__":
    uvicorn.run(app, host=settings.IP_ADDRESS, port=settings.PORT)
