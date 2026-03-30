import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app import app
from src.auth.service import GitHubAuthError
from src.core.session import SESSION_CACHE
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
        "created_at": now,
    }
    mock_service = AsyncMock()
    mock_service.handle_callback.return_value = mock_result
    # login_user is synchronous, so we must use MagicMock to avoid RuntimeWarning
    mock_service.login_user = MagicMock()

    def login_user_side_effect(response, user_info):
        session_id = "test-session-id"
        SESSION_CACHE[session_id] = {
            "username": user_info["username"],
            "access_token": user_info["access_token"],
            "created_at": user_info["created_at"],
        }
        response.set_cookie(key="user_session", value=session_id)
        return session_id

    mock_service.login_user.side_effect = login_user_side_effect

    app.dependency_overrides[get_auth_service] = lambda: mock_service

    try:
        response = client.get("/auth/github/callback")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["created_at"] == now

        # Check if cookie is set by hitting /auth/me
        session_cookie = response.cookies.get("user_session")
        client.cookies.set("user_session", session_cookie)
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


def test_me_route_authenticated(client, auth_cookie):
    """Test the /auth/me route with auth cookie."""
    response = client.get("/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == auth_cookie["username"]
    assert "access_token" not in data


def test_me_route_unauthenticated(client):
    """Test the /auth/me route without auth cookie."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated or session expired"}


def test_logout_route(client):
    """Test the /auth/logout route."""
    mock_service = AsyncMock()
    app.dependency_overrides[get_auth_service] = lambda: mock_service

    try:
        client.cookies.set("user_session", "some-session-id")
        response = client.post("/auth/logout")

        assert response.status_code == 200
        assert response.json() == {"message": "Logged out successfully"}
        # logout_user should have been called
        mock_service.logout_user.assert_called_once()
        # response cookie should be cleared but client depends on the test client handling
        assert (
            "user_session" not in response.cookies
            or response.cookies["user_session"] == ""
        )
    finally:
        app.dependency_overrides.clear()
