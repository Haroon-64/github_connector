from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.github.client import GitHubClient
from src.github.service import GitHubService
from src.models.error import AuthError, NotFoundError, RateLimitError


@pytest.fixture
def github_client():
    return GitHubClient("fake_token")


@pytest.mark.anyio
@patch("httpx.AsyncClient.request")
async def test_get_repositories_success(mock_request, github_client):
    mock_response = httpx.Response(200, json=[{"name": "repo1"}])
    mock_request.return_value = mock_response

    repos = await GitHubService(github_client).get_repositories("user")
    assert len(repos) == 1
    assert repos[0]["name"] == "repo1"
    mock_request.assert_called_once()


@pytest.mark.anyio
@patch("httpx.AsyncClient.request")
async def test_pagination(mock_request, github_client):
    mock_headers = {"Link": '<https://api.github.com/user/repos?page=2>; rel="next"'}

    page1 = httpx.Response(200, headers=mock_headers, json=[{"name": "repo1"}])
    page2 = httpx.Response(200, json=[{"name": "repo2"}])

    mock_request.side_effect = [page1, page2]

    repos = await GitHubService(github_client).get_repositories()

    assert len(repos) == 2
    assert repos[0]["name"] == "repo1"
    assert repos[1]["name"] == "repo2"
    assert mock_request.call_count == 2


@pytest.mark.anyio
async def test_raise_for_status_not_found(github_client):
    mock_response = httpx.Response(404)
    with pytest.raises(NotFoundError):
        github_client._raise_for_status(mock_response)


@pytest.mark.anyio
async def test_raise_for_status_rate_limit(github_client):
    mock_response = httpx.Response(429)
    with pytest.raises(RateLimitError):
        github_client._raise_for_status(mock_response)


@pytest.mark.anyio
async def test_raise_for_status_auth_error(github_client):
    mock_response = httpx.Response(401)
    with pytest.raises(AuthError):
        github_client._raise_for_status(mock_response)


@pytest.mark.anyio
async def test_client_aclose(github_client):
    with patch("httpx.AsyncClient.aclose", new_callable=AsyncMock) as mock_aclose:
        # Access client property to initialize it
        _ = github_client.client
        await github_client.aclose()
        mock_aclose.assert_called_once()
        assert github_client._client is None
