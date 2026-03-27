import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from src.auth.routes import auth_router
from src.core.config import settings
from src.core.logging import setup_logging
from src.github.routes import github_router
from src.models.error import ApiError, ErrorResponse

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


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    content = ErrorResponse(
        type=exc.type, status=exc.status, details=exc.details
    ).model_dump()
    return JSONResponse(
        status_code=exc.status,
        content=content,
    )


if __name__ == "__main__":
    uvicorn.run(app, host=settings.IP_ADDRESS, port=settings.PORT)
