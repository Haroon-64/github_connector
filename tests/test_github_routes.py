import secrets
import time
from unittest.mock import AsyncMock

import pytest

from src.app import app
from src.core.session import SESSION_CACHE
from src.dependencies.github import get_github_client, get_optional_github_client
from src.models.error import NotFoundError, RateLimitError, ValidationError


@pytest.fixture
def auth_cookie(client):
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


def test_list_repos_success(client, auth_cookie):
    mock_client = AsyncMock()
    mock_client.get_repositories.return_value = [
        {
            "id": 1,
            "name": "repo1",
            "full_name": "user/repo1",
            "private": False,
            "owner": {},
            "html_url": "url1",
            "fork": False,
        }
    ]
    app.dependency_overrides[get_optional_github_client] = lambda: mock_client

    try:
        response = client.get("/github/repos")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "repo1"
    finally:
        app.dependency_overrides.clear()


def test_list_repos_not_found(client, auth_cookie):
    mock_client = AsyncMock()
    mock_client.get_repositories.side_effect = NotFoundError()
    app.dependency_overrides[get_optional_github_client] = lambda: mock_client

    try:
        response = client.get("/github/repos?username=nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"
    finally:
        app.dependency_overrides.clear()


def test_create_issue_success(client, auth_cookie):
    mock_client = AsyncMock()
    mock_client.create_issue.return_value = {
        "id": 123,
        "number": 1,
        "title": "Test Issue",
        "state": "open",
        "user": {},
    }
    app.dependency_overrides[get_github_client] = lambda: mock_client

    try:
        issue_data = {"title": "Test Issue", "body": "Details"}
        response = client.post("/github/repos/owner/repo/issues", json=issue_data)
        assert response.status_code == 200
        assert response.json()["title"] == "Test Issue"
    finally:
        app.dependency_overrides.clear()


def test_create_issue_validation_error(client, auth_cookie):
    mock_client = AsyncMock()
    mock_client.create_issue.side_effect = ValidationError(
        status=422, details="Title is required"
    )
    app.dependency_overrides[get_github_client] = lambda: mock_client

    try:
        response = client.post(
            "/github/repos/owner/repo/issues",
            json={"title": "Valid title", "body": "invalid meta"},
        )
        assert response.status_code == 422
        assert "Title is required" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_create_pull_success(client, auth_cookie):
    mock_client = AsyncMock()
    mock_client.create_pull_request.return_value = {
        "id": 42,
        "number": 10,
        "title": "PR",
        "state": "open",
        "user": {},
        "head": {},
        "base": {},
        "html_url": "url",
    }
    app.dependency_overrides[get_github_client] = lambda: mock_client

    try:
        pr_data = {"title": "PR", "head": "feat", "base": "main"}
        response = client.post("/github/repos/owner/repo/pulls", json=pr_data)
        assert response.status_code == 200
        assert response.json()["number"] == 10
    finally:
        app.dependency_overrides.clear()


def test_list_commits_rate_limit(client, auth_cookie):
    mock_client = AsyncMock()
    mock_client.get_commits.side_effect = RateLimitError(retry_after=60)
    app.dependency_overrides[get_optional_github_client] = lambda: mock_client

    try:
        response = client.get("/github/repos/owner/repo/commits")
        assert response.status_code == 403
        assert response.json()["detail"] == "Rate limit exceeded"
        assert float(response.headers["Retry-After"]) == pytest.approx(60.0)
    finally:
        app.dependency_overrides.clear()
