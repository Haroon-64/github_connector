from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.github.client import GitHubClient
from src.github.service import GitHubService
from src.models.error import AuthError, NotFoundError, RateLimitError


@pytest.fixture
def github_client():
    return GitHubClient("fake_token")


@pytest.fixture
def mock_retry_policy():
    """Mock retry policy that passes through the callback."""
    policy = MagicMock()
    
    async def execute_with_retries(callback, access_token=None):
        return await callback()
    
    policy.execute_with_retries = AsyncMock(side_effect=execute_with_retries)
    policy.update_rate_limit_state = MagicMock()
    return policy


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
@patch("httpx.AsyncClient.request")
async def test_make_request(mock_request, github_client):
    """Test the _make_request callback method."""
    mock_response = httpx.Response(200, json={"data": "test"})
    mock_request.return_value = mock_response

    response = await github_client._make_request(
        "GET",
        "https://api.github.com/test",
        params={"key": "value"},
        json_data=None,
    )

    assert response.status_code == 200
    assert response.json() == {"data": "test"}
    mock_request.assert_called_once_with(
        "GET",
        "https://api.github.com/test",
        params={"key": "value"},
        json=None,
    )


@pytest.mark.anyio
async def test_make_request_with_json_data(github_client):
    """Test _make_request with JSON data."""
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = httpx.Response(201, json={"created": True})
        mock_request.return_value = mock_response

        response = await github_client._make_request(
            "POST",
            "https://api.github.com/test",
            params=None,
            json_data={"name": "test"},
        )

        assert response.status_code == 201
        mock_request.assert_called_once_with(
            "POST",
            "https://api.github.com/test",
            params=None,
            json={"name": "test"},
        )


@pytest.mark.anyio
async def test_fetch_page_delegates_to_retry_policy(github_client, mock_retry_policy):
    """Test that _fetch_page_with_retries delegates to retry policy."""
    github_client.retry_policy = mock_retry_policy
    
    mock_response = httpx.Response(200, json=[{"name": "repo1"}])
    
    with patch.object(github_client, "_make_request", return_value=mock_response) as mock_make_request:
        result = await github_client._fetch_page_with_retries(
            "GET",
            "https://api.github.com/test",
            None,
            None,
        )
        
        # Verify retry policy was called with correct parameters
        mock_retry_policy.execute_with_retries.assert_called_once()
        call_args = mock_retry_policy.execute_with_retries.call_args
        
        # Verify access token was passed (second positional argument)
        assert call_args[0][1] == "fake_token"
        
        # Verify response was finalized correctly
        assert result == ([{"name": "repo1"}], None)


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


# ---------------------------------------------------------------------------
# Integration tests: GitHubClient + GitHubRetryPolicy
# Patches httpx.AsyncClient.request at the HTTP level to exercise the real
# retry policy without real network calls or real delays.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@patch("asyncio.sleep", new_callable=AsyncMock)
@patch("httpx.AsyncClient.request")
async def test_integration_retry_on_rate_limit(mock_request, mock_sleep):
    """End-to-end: client retries on 429 and succeeds on second attempt.

    Requirements: 4.2, 4.3, 5.5
    """
    rate_limit_response = httpx.Response(429, headers={"retry-after": "0.01"})
    success_response = httpx.Response(200, json={"name": "repo1"})
    mock_request.side_effect = [rate_limit_response, success_response]

    client = GitHubClient("fake_token")
    result = await client.request("GET", "/repos/user/repo")

    assert result == {"name": "repo1"}
    assert mock_request.call_count == 2
    # sleep was called at least once for the retry wait
    assert mock_sleep.call_count >= 1


@pytest.mark.anyio
@patch("asyncio.sleep", new_callable=AsyncMock)
@patch("httpx.AsyncClient.request")
async def test_integration_retry_on_server_error(mock_request, mock_sleep):
    """End-to-end: client retries on 500 and succeeds on second attempt.

    Requirements: 4.2, 4.3, 5.5
    """
    server_error_response = httpx.Response(500)
    success_response = httpx.Response(200, json=[{"name": "repo1"}])
    mock_request.side_effect = [server_error_response, success_response]

    client = GitHubClient("fake_token")
    result = await client.request("GET", "/users/user/repos")

    assert result == [{"name": "repo1"}]
    assert mock_request.call_count == 2
    assert mock_sleep.call_count >= 1


@pytest.mark.anyio
@patch("httpx.AsyncClient.request")
async def test_integration_pagination_works(mock_request):
    """End-to-end: pagination accumulates all pages correctly.

    Requirements: 4.3
    """
    page1 = httpx.Response(
        200,
        headers={"Link": '<https://api.github.com/users/user/repos?page=2>; rel="next"'},
        json=[{"name": "repo1"}],
    )
    page2 = httpx.Response(200, json=[{"name": "repo2"}, {"name": "repo3"}])
    mock_request.side_effect = [page1, page2]

    client = GitHubClient("fake_token")
    result = await client.request("GET", "/users/user/repos")

    assert result == [{"name": "repo1"}, {"name": "repo2"}, {"name": "repo3"}]
    assert mock_request.call_count == 2


@pytest.mark.anyio
@patch("httpx.AsyncClient.request")
async def test_integration_rate_limit_state_updated_across_requests(mock_request):
    """End-to-end: rate limit state is updated from response headers across requests.

    Requirements: 4.2, 5.5
    """
    import time

    reset_time = str(int(time.time()) + 3600)

    response1 = httpx.Response(
        200,
        headers={
            "x-ratelimit-remaining": "4999",
            "x-ratelimit-reset": reset_time,
        },
        json=[{"name": "repo1"}],
    )
    response2 = httpx.Response(
        200,
        headers={
            "x-ratelimit-remaining": "4998",
            "x-ratelimit-reset": reset_time,
        },
        json=[{"name": "repo2"}],
    )
    mock_request.side_effect = [response1, response2]

    client = GitHubClient("fake_token")

    await client.request("GET", "/users/user/repos1")
    state_after_first = client.retry_policy._rate_limit_state.get("fake_token")
    assert state_after_first is not None
    assert state_after_first["remaining"] == 4999

    await client.request("GET", "/users/user/repos2")
    state_after_second = client.retry_policy._rate_limit_state.get("fake_token")
    assert state_after_second is not None
    assert state_after_second["remaining"] == 4998


# ---------------------------------------------------------------------------
# Property-based tests for GitHubClient
# ---------------------------------------------------------------------------

from hypothesis import given, settings as h_settings
from hypothesis import strategies as st


@h_settings(max_examples=20, deadline=None)
@given(
    pages=st.lists(
        st.lists(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
                min_size=0,
                max_size=5,
            ),
            min_size=0,
            max_size=5,
        ),
        min_size=1,
        max_size=6,
    )
)
def test_property_pagination_accumulates_all_pages_correctly(pages):
    """Property 4: Pagination accumulates all pages correctly.

    **Validates: Requirements 4.3**

    Generate arbitrary number of pages with random data and verify all pages
    are accumulated in the correct order.
    """
    import asyncio
    import json
    from unittest.mock import AsyncMock, patch

    base_url = "https://api.github.com"

    def make_responses(pages):
        responses = []
        for i, page_data in enumerate(pages):
            is_last = i == len(pages) - 1
            if is_last:
                headers = {}
            else:
                next_url = f"{base_url}/users/user/repos?page={i + 2}"
                headers = {"Link": f'<{next_url}>; rel="next"'}
            responses.append(
                httpx.Response(200, headers=headers, json=page_data)
            )
        return responses

    async def run():
        client = GitHubClient("fake_token")
        responses = make_responses(pages)
        with patch("httpx.AsyncClient.request", side_effect=responses):
            result = await client.request("GET", "/users/user/repos")
        return result

    result = asyncio.run(run())

    expected = []
    for page in pages:
        expected.extend(page)

    assert result == expected
