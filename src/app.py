import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.auth.routes import auth_router
from src.camunda.routes import camunda_router
from src.camunda.worker import start_zeebe_worker
from src.core.config import settings
from src.core.logging import setup_logging
from src.github.routes import github_router
from src.models.error import ApiError, ErrorResponse

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_zeebe_worker())
    yield
    task.cancel()


app = FastAPI(
    title="GitHub Connector",
    version="1.0.0",
    description="FastAPI-based GitHub Connector",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=settings.OAUTH_SECRET)
app.include_router(auth_router, prefix="/auth")
app.include_router(github_router, prefix="/github")
app.include_router(camunda_router, prefix="/camunda")

app.mount("/", StaticFiles(directory="UI/dist", html=True), name="static")

@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    headers = {}
    if hasattr(exc, "retry_after") and exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)

    content = ErrorResponse(
        type=exc.type, status=exc.status, details=exc.details
    ).model_dump()

    if isinstance(exc.details, str):
        content["detail"] = exc.details
    elif exc.type == "rate_limit":
        content["detail"] = "Rate limit exceeded"
    elif exc.type == "not_found":
        content["detail"] = "Not found"
    elif exc.type == "auth":
        content["detail"] = "Authentication failed"
    else:
        content["detail"] = f"{exc.type.capitalize()} error occurred"

    logger.error(
        "api_error",
        type=exc.type,
        status=exc.status,
        details=exc.details,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status,
        content=content,
        headers=headers,
    )


if __name__ == "__main__":
    uvicorn.run(app, host=settings.IP_ADDRESS, port=settings.PORT)
