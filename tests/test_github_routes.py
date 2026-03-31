import pytest

from src.models.error import NotFoundError, RateLimitError, ValidationError


def test_list_repos_success(client, auth_cookie, mock_github):
    mock = mock_github(required=False)
    mock.get_repositories.return_value = [
        {
            "id": 1,
            "name": "repo1",
            "full_name": "user/repo1",
            "private": False,
            "owner": {
                "login": "user",
                "id": 42,
                "avatar_url": "url",
                "html_url": "url",
                "type": "User",
            },
            "html_url": "url1",
            "fork": False,
        }
    ]

    response = client.get("/github/repos")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "repo1"


def test_list_repos_not_found(client, auth_cookie, mock_github):
    mock = mock_github(required=False)
    mock.get_repositories.side_effect = NotFoundError()

    response = client.get("/github/repos?username=nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not found"


def test_create_issue_success(client, auth_cookie, mock_github):
    mock = mock_github(required=True)
    mock.create_issue.return_value = {
        "id": 123,
        "number": 1,
        "title": "Test Issue",
        "state": "open",
        "user": {
            "login": "user",
            "id": 42,
            "avatar_url": "url",
            "html_url": "url",
            "type": "User",
        },
    }

    issue_data = {"title": "Test Issue", "body": "Details"}
    response = client.post("/github/repos/owner/repo/issues", json=issue_data)
    assert response.status_code == 200
    assert response.json()["title"] == "Test Issue"


def test_create_issue_validation_error(client, auth_cookie, mock_github):
    mock = mock_github(required=True)
    mock.create_issue.side_effect = ValidationError(
        status=422, details="Title is required"
    )

    response = client.post(
        "/github/repos/owner/repo/issues",
        json={"title": "Valid title", "body": "invalid meta"},
    )
    assert response.status_code == 422
    assert "Title is required" in response.json()["detail"]


def test_create_pull_success(client, auth_cookie, mock_github):
    mock = mock_github(required=True)
    mock.create_pull_request.return_value = {
        "id": 42,
        "number": 10,
        "title": "PR",
        "state": "open",
        "user": {
            "login": "user",
            "id": 42,
            "avatar_url": "url",
            "html_url": "url",
            "type": "User",
        },
        "head": {},
        "base": {},
        "html_url": "url",
    }

    pr_data = {"title": "PR", "head": "feat", "base": "main"}
    response = client.post("/github/repos/owner/repo/pulls", json=pr_data)
    assert response.status_code == 200
    assert response.json()["number"] == 10


def test_list_commits_rate_limit(client, auth_cookie, mock_github):
    mock = mock_github(required=False)
    mock.get_commits.side_effect = RateLimitError(retry_after=60)

    response = client.get("/github/repos/owner/repo/commits")
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded"
    assert float(response.headers["Retry-After"]) == pytest.approx(60.0)
