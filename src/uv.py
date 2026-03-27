import os

import pytest
import uvicorn

from src.core.config import settings


def start_dev() -> None:
    os.environ["LOG_LEVEL"] = "debug"

    uvicorn.run(
        "src.app:app",
        host=settings.IP_ADDRESS,
        port=settings.PORT,
        reload=True,
        log_level="debug",
    )


def start_prod() -> None:
    os.environ["LOG_LEVEL"] = "info"

    uvicorn.run(
        "src.app:app",
        host=settings.IP_ADDRESS,
        port=settings.PORT,
        log_level="info",
    )


def tests() -> None:
    raise SystemExit(pytest.main())


def check() -> None:
    os.system("ruff format src")
    os.system("ruff check --fix src")
    os.system("mypy src")
