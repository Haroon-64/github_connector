import json
from unittest.mock import AsyncMock

from src.app import app
from src.auth.service.github import GitHubAuthError
from src.dependencies.auth import get_auth_service


def test_github_login_route(client):
    """Test the /auth/github/login route."""
    mock_service = AsyncMock()
    mock_service.get_login_url.return_value = "https://github.com/authorize"

    app.dependency_overrides[get_auth_service] = lambda: mock_service

    try:
        response = client.get("/auth/github/login")
        assert response.status_code == 200
        assert response.json() == {"login_url": "https://github.com/authorize"}
    finally:
        app.dependency_overrides.clear()


def test_github_callback_route_success(client):
    """Test the /auth/github/callback route success."""
    mock_result = {
        "username": "testuser",
        "access_token": "token123",
        "token_type": "bearer",
    }
    mock_service = AsyncMock()
    mock_service.handle_callback.return_value = mock_result

    app.dependency_overrides[get_auth_service] = lambda: mock_service

    try:
        response = client.get("/auth/github/callback")

        assert response.status_code == 200
        assert response.json()["username"] == "testuser"
        # Check if cookie is set by hitting /auth/me
        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "testuser"
    finally:
        app.dependency_overrides.clear()


def test_github_callback_route_failure(client):
    """Test the /auth/github/callback route failure."""
    mock_service = AsyncMock()
    mock_service.handle_callback.side_effect = GitHubAuthError("OAuth failed", 400)

    app.dependency_overrides[get_auth_service] = lambda: mock_service

    try:
        response = client.get("/auth/github/callback")

        assert response.status_code == 400
        assert response.json() == {"detail": "OAuth failed"}
    finally:
        app.dependency_overrides.clear()


def test_me_route_authenticated(client):
    """Test the /auth/me route with auth cookie."""
    user_data = {"username": "testuser", "access_token": "token123"}
    cookie_value = json.dumps(user_data)

    client.cookies.set("user_session", cookie_value)
    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json() == user_data


def test_me_route_unauthenticated(client):
    """Test the /auth/me route without auth cookie."""
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
