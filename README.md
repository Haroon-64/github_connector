# GitHub Connector

A FastAPI-based application designed to interface with the GitHub API. It features a complete OAuth2 authentication flow, secure session management, and GitHub client with error handling and rate limiting.

## Features

- **GitHub OAuth2 Authentication**: Secure login, callback handling, and logout with token revocation.
- **Session Management**: Uses encrypted, HTTP-only cookies for secure user sessions.
- **GitHub Client**:
  - **Automatic Retries**: Implements exponential backoff for network and server errors.
  - **Rate Limit Handling**: waits for rate limit resets based on GitHub's API headers.
  - **Pagination Support**: Automatically handles `Link` headers to fetch all pages of results.
  - **Type-Safe Models**: error mapping to specific exception types.
- **API Coverage**:
  - **Repositories**: List user and organization repositories.
  - **Issues**: Create and list issues for any repository.
  - **Pull Requests**: Create pull requests.
  - **Commits**: Fetch commit history and filter by SHA.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended)
- GitHub OAuth App credentials (Client ID and Client Secret)

## Installation

1. Clone the repository:

   ```bash
   git clone git@github.com:Haroon-64/github_connector.git
   cd github_connector
   ```

2. Create a `.env` file from the template:

   ```bash
   cp .env.example .env
   ```

3. Configure OAuth
    1. Go to [https://github.com/settings/applications/new](https://github.com/settings/applications/new)
    2. Fill in the following fields:
          - **Application name**: GitHub Connector
          - **Homepage URL**: <http://127.0.0.1:8000>
          - **Authorization callback URL**: <http://127.0.0.1:8000/auth/github/callback>
    3. Click on **Register application**
    4. Copy the **Client ID** and **Client Secret**
    5. Paste them in the `.env` file
    - `OAUTH_CLIENT_ID`: Your GitHub OAuth App Client ID.
    - `OAUTH_SECRET`: A secure key for session encryption. Generated from github oauth app.

## Running the Application

Using `uv`:

```bash
uv sync
uv run dev
```

The API will be available at `http://127.0.0.1:8000`.

## Login

1. Go to [http://127.0.0.1:8000/auth/github/login](http://127.0.0.1:8000/auth/github/login)
2. Click on **Login url**
3. Authorize the application
4. You will be redirected to the callback URL
5. You will see the following response:

```json
{
  "token_type": "bearer",
  "username": "<USERNAME>",
  "created_at": "<CREATED_AT>"
}
```

- You can use /auth/logout to log out and delete the oauth token.

## Documentation

- **Interactive API Docs**: Once running, visit [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.
- **Architecture**: See [docs/architecture.md](docs/architecture.md) for a deep dive into the system design.
- **Design Decisions**: See [docs/design_decisions.md](docs/design_decisions.md) for rationale behind technical choices.

### Example Request

```sh
curl -X POST http://localhost:8000/github/repos/octocat/hello-world/issues \
-H "Authorization: Bearer <TOKEN>" \
-d '{"title":"Bug","body":"test"}'
```

## Requirements Compliance

- **1. Authentication**: Implemented **OAuth 2.0** with secure session management via HTTP-only cookies and token revocation on logout.
- **2. API Integration**:
  - Fetch user/org repositories.
  - Create and list issues.
  - Create pull requests.
  - Fetch commits.
- **3. Interface**: Exposed as a **REST API** using FastAPI with auto-generated Swagger/Redoc documentation.
- **4. Tech Stack**: Built with **Python 3.12+** and **FastAPI**, following modern asynchronous patterns.
- **5. Code Spec**:
  - **Modularity**: Clearly separated routes, services, models, and core configuration.
  - **Error Handling**: Custom exception hierarchy and exponential backoff for API resilience. Referenced [from](https://oneuptime.com/blog/post/2025-01-06-python-retry-exponential-backoff/view) 
  - **Testing**: test suite covering authentication flow and GitHub routes.

## Project Structure

```text
src/
├── auth/           # OAuth logic and routes
├── core/           # Configuration and logging
├── github/         # GitHub API client and business logic
├── models/         # Pydantic data models
└── dependencies/   # FastAPI dependency injection
```
