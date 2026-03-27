from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.app import app


@pytest.fixture
def client():
    """Fixture for FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def mock_oauth():
    """Fixture for mocked Authlib OAuth."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_request():
    """Fixture for mocked Starlette Request."""
    request = MagicMock()
    request.session = {}
    return request
