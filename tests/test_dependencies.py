import secrets

import pytest
from fastapi import HTTPException

from src.auth.service import GitHubAuthService
from src.core.session import SESSION_CACHE, TOKEN_CACHE
from src.dependencies.auth import (
    auth_provider,
    get_auth_service,
)
from src.dependencies.github import github_provider
from src.github.client import GitHubClient
from src.github.service import GitHubService


def test_get_auth_service():
    service = get_auth_service()
    assert isinstance(service, GitHubAuthService)


@pytest.mark.anyio
async def test_auth_provider_session_valid(mock_request):
    session_id = secrets.token_urlsafe(32)
    user_data = {"username": "testuser", "access_token": "token"}
    SESSION_CACHE[session_id] = user_data
    mock_request.cookies = {"user_session": session_id}

    dep = auth_provider(required=True)
    user = await dep(mock_request)
    assert user == user_data


@pytest.mark.anyio
async def test_auth_provider_session_missing_required(mock_request):
    mock_request.cookies = {}
    dep = auth_provider(required=True)
    with pytest.raises(HTTPException) as exc:
        await dep(mock_request)
    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_auth_provider_session_missing_optional(mock_request):
    mock_request.cookies = {}
    dep = auth_provider(required=False)
    user = await dep(mock_request)
    assert user is None


@pytest.mark.anyio
async def test_auth_provider_bearer_valid(mock_request):
    token = "some-token"
    mock_request.headers = {"Authorization": f"Bearer {token}"}
    TOKEN_CACHE[token] = "api_user"

    dep = auth_provider(required=True)
    user = await dep(mock_request)
    assert user["access_token"] == token
    assert user["username"] == "api_user"


from unittest.mock import AsyncMock, patch

@pytest.mark.anyio
async def test_auth_provider_bearer_invalid_required(mock_request):
    mock_request.headers = {"Authorization": "Bearer invalid"}
    # Mocking GitHubClient to return 401 error
    with patch("src.dependencies.auth.GitHubClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.request = AsyncMock(side_effect=HTTPException(status_code=401))
        mock_instance.aclose = AsyncMock()

        dep = auth_provider(required=True)
        with pytest.raises(HTTPException) as exc:
            await dep(mock_request)
        assert exc.value.status_code == 401


def test_github_provider():
    user = {"access_token": "test-token"}
    dependency = github_provider(required=True)
    service = dependency(user=user)
    assert isinstance(service, GitHubService)
    assert isinstance(service.client, GitHubClient)
    assert service.client._access_token == "test-token"
