import json
import time
from unittest.mock import AsyncMock

import pytest
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
    now = int(time.time())
    mock_result = {
        "username": "testuser",
        "access_token": "token123",
        "token_type": "bearer",
        "expires_in": 3600,
        "created_at": now,
    }
    mock_service = AsyncMock()
    mock_service.handle_callback.return_value = mock_result

    app.dependency_overrides[get_auth_service] = lambda: mock_service

    try:
        response = client.get("/auth/github/callback")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["access_token"] == "token123"
        assert data["created_at"] == now

        # Check if cookie is set by hitting /auth/me
        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["username"] == "testuser"
        # access_token is no longer in UserResponse
        assert "access_token" not in me_data
        assert me_data["created_at"] == now
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
    now = int(time.time())
    user_data = {
        "username": "testuser",
        "access_token": "token123",
        "created_at": now,
        "expires_at": now + 3600,
    }
    cookie_value = json.dumps(user_data)

    client.cookies.set("user_session", cookie_value)
    response = client.get("/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user_data["username"]
    assert "access_token" not in data


def test_me_route_unauthenticated(client):
    """Test the /auth/me route without auth cookie."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated or session expired"}


def test_logout_route(client):
    """Test the /auth/logout route."""
    client.cookies.set("user_session", "some-data")
    response = client.post("/auth/logout")
    
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully"}
    assert "user_session" not in response.cookies or response.cookies["user_session"] == ""
