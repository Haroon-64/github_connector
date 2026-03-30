from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.auth.service import GitHubAuthError, GitHubAuthService


@pytest.mark.anyio
async def test_get_login_url_success(mock_oauth, mock_request):
    """Test generating login URL successfully."""
    mock_redirect = MagicMock()
    mock_redirect.headers = {"Location": "https://github.com/authorize"}
    mock_oauth.github.authorize_redirect = AsyncMock(return_value=mock_redirect)

    service = GitHubAuthService(mock_oauth)
    url = await service.get_login_url(mock_request, "http://callback")

    assert url == "https://github.com/authorize"
    mock_oauth.github.authorize_redirect.assert_called_once_with(
        mock_request, "http://callback"
    )


@pytest.mark.anyio
async def test_get_login_url_failure(mock_oauth, mock_request):
    """Test generating login URL with failure."""
    mock_oauth.github.authorize_redirect = AsyncMock(
        side_effect=Exception("Authlib error")
    )

    service = GitHubAuthService(mock_oauth)
    with pytest.raises(GitHubAuthError) as exc:
        await service.get_login_url(mock_request, "http://callback")

    assert "Failed to generate login URL" in str(exc.value)


@pytest.mark.anyio
async def test_handle_callback_success(mock_oauth, mock_request):
    """Test handling callback successfully."""
    mock_token = {"access_token": "token123", "token_type": "bearer"}
    mock_user_data = {"login": "testuser"}

    mock_oauth.github.authorize_access_token = AsyncMock(return_value=mock_token)
    mock_user_info = MagicMock()
    mock_user_info.json.return_value = mock_user_data
    mock_oauth.github.get = AsyncMock(return_value=mock_user_info)

    service = GitHubAuthService(mock_oauth)
    result = await service.handle_callback(mock_request)

    assert result["username"] == "testuser"
    assert result["access_token"] == "token123"
    mock_oauth.github.authorize_access_token.assert_called_once_with(mock_request)


@pytest.mark.anyio
async def test_handle_callback_failure(mock_oauth, mock_request):
    """Test handling callback with failure."""
    mock_oauth.github.authorize_access_token = AsyncMock(
        side_effect=Exception("Callback error")
    )

    service = GitHubAuthService(mock_oauth)
    with pytest.raises(GitHubAuthError) as exc:
        await service.handle_callback(mock_request)

    assert "OAuth callback failed" in str(exc.value)

@pytest.mark.anyio
@patch("httpx.AsyncClient.request")
async def test_revoke_token_success(mock_request):
    """Test revoking token successfully."""
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_request.return_value = mock_response

    mock_oauth = MagicMock()
    service = GitHubAuthService(mock_oauth)

    # Should not raise exception
    await service.revoke_token("token123")
    mock_request.assert_called_once()


@pytest.mark.anyio
@patch("httpx.AsyncClient.request")
async def test_revoke_token_failure(mock_request):
    """Test revoking token with failure being gracefully caught."""
    mock_request.side_effect = Exception("Network error")

    mock_oauth = MagicMock()
    service = GitHubAuthService(mock_oauth)

    # Should catch exception and log it, not raise
    await service.revoke_token("token123")
    mock_request.assert_called_once()
