import secrets

import anyio
import pytest
from fastapi import HTTPException

from src.auth.service.github import GitHubAuthService
from src.core.session import SESSION_CACHE, TOKEN_CACHE
from src.dependencies.auth import (
    get_auth_service,
    get_current_user,
    get_optional_user,
    get_session_user,
)
from src.dependencies.github import get_github_client
from src.github.client import GitHubClient


def test_get_auth_service():
    service = get_auth_service()
    assert isinstance(service, GitHubAuthService)

def test_get_session_user_valid_cookie(mock_request):
    session_id = secrets.token_urlsafe(32)
    SESSION_CACHE[session_id] = {"username": "testuser", "access_token": "token"}
    mock_request.cookies = {"user_session": session_id}
    user = get_session_user(mock_request)
    assert user is not None
    assert user["username"] == "testuser"
    assert user["access_token"] == "token"

def test_get_session_user_missing_cookie(mock_request):
    mock_request.cookies = {}
    user = get_session_user(mock_request)
    assert user is None

def test_get_session_user_invalid_cookie(mock_request):
    mock_request.cookies = {"user_session": "not-a-real-session"}
    user = get_session_user(mock_request)
    assert user is None

def test_get_optional_user_with_session(mock_request):
    mock_request.headers = {}
    user_dict = {"username": "testuser", "access_token": "token"}

    async def run_test():
        return await get_optional_user(mock_request, user=user_dict)

    user = anyio.run(run_test)
    assert user == user_dict

def test_get_optional_user_with_auth_header(mock_request):
    mock_request.headers = {"Authorization": "Bearer some-token"}
    TOKEN_CACHE["some-token"] = "api_user"

    async def run_test():
        return await get_optional_user(mock_request, user=None)

    user = anyio.run(run_test)
    assert user["access_token"] == "some-token"
    assert user["username"] == "api_user"

def test_get_optional_user_unauthorized(mock_request):
    mock_request.headers = {}

    async def run_test():
        return await get_optional_user(mock_request, user=None)

    user = anyio.run(run_test)
    assert user is None

def test_get_current_user_authorized():
    user_dict = {"username": "testuser", "access_token": "token"}
    user = get_current_user(user=user_dict)
    assert user == user_dict

def test_get_current_user_unauthorized():
    with pytest.raises(HTTPException) as exc:
        get_current_user(user=None)
    assert exc.value.status_code == 401
    assert "Not authenticated or session expired" in str(exc.value.detail)

def test_get_github_client():
    user = {"access_token": "test-token"}
    client = get_github_client(current_user=user)
    assert isinstance(client, GitHubClient)
