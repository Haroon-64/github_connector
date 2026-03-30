import secrets
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.core.session import SESSION_CACHE
from src.dependencies.github import github_provider


@pytest.fixture
def client():
    """Fixture for FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def auth_cookie(client):
    """Fixture to set up an authenticated session."""
    now = int(time.time())
    user_data = {
        "username": "testuser",
        "access_token": "gho_test_token",
        "created_at": now,
    }

    session_id = secrets.token_urlsafe(32)
    SESSION_CACHE[session_id] = user_data
    client.cookies.set("user_session", session_id)
    return user_data


@pytest.fixture
def mock_github():
    """Fixture to mock GitHubService dependency with automatic cleanup."""
    mock = AsyncMock()

    def _override(required: bool = False):
        app.dependency_overrides[github_provider(required=required)] = lambda: mock
        return mock

    yield _override
    app.dependency_overrides.clear()


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
    request.headers = {}
    request.cookies = {}
    return request
