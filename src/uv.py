import os

import pytest
import uvicorn

from src.core.config import settings


def start_dev():
    os.environ["LOG_LEVEL"] = "debug"

    uvicorn.run(
        "src.app:app",
        host=settings.IP_ADDRESS,
        port=settings.PORT,
        reload=True,
        log_level="debug",
    )

def start_prod():
    os.environ["LOG_LEVEL"] = "info"

    uvicorn.run(
        "src.app:app",
        host=settings.IP_ADDRESS,
        port=settings.PORT,
        log_level="info",
    )

def tests():
    raise SystemExit(pytest.main())
