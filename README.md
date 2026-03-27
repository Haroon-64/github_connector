# GitHub Connector

A robust FastAPI-based application designed to interface with the GitHub API. It features a complete OAuth2 authentication flow, secure session management, and a resilient GitHub client with advanced error handling and rate limiting.

## Features

- **GitHub OAuth2 Authentication**: Secure login, callback handling, and logout with token revocation.
- **Session Management**: Uses encrypted, HTTP-only cookies for secure user sessions.
- **Resilient GitHub Client**:
  - **Automatic Retries**: Implements exponential backoff for network and server errors.
  - **Rate Limit Handling**: Smartly waits for rate limit resets based on GitHub's API headers.
  - **Pagination Support**: Automatically handles `Link` headers to fetch all pages of results.
  - **Type-Safe Models**: Robust error mapping to specific exception types.
- **Comprehensive API Coverage**:
  - **Repositories**: List user and organization repositories.
  - **Issues**: Create and list issues for any repository.
  - **Pull Requests**: Create pull requests.
  - **Commits**: Fetch commit history and filter by SHA.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- GitHub OAuth App credentials (Client ID and Client Secret)

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd github_connector
   ```

2. Create a `.env` file from the template:

   ```bash
   cp .env.example .env
   ```

3. Configure your environment variables in `.env`:
   - `GITHUB_CLIENT_ID`: Your GitHub OAuth App Client ID.
   - `GITHUB_CLIENT_SECRET`: Your GitHub OAuth App Client Secret.
   - `OAUTH_SECRET`: A secure key for session encryption.

## Running the Application

Using `uv`:

```bash
uv run dev
```

Using standard Python:

```bash
python -m src.app
```

The API will be available at `http://localhost:8000`.

## Documentation

- **Interactive API Docs**: Once running, visit [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.
- **Architecture**: See [docs/architecture.md](docs/architecture.md) for a deep dive into the system design.
- **Design Decisions**: See [docs/design_decisions.md](docs/design_decisions.md) for rationale behind technical choices.

## Requirements Compliance

- **1. Authentication**: Implemented **OAuth 2.0** with secure session management via HTTP-only cookies and token revocation on logout.
- **2. API Integration**: Implemented **all mandatory and bonus actions**:
  - Fetch user/org repositories.
  - Create and list issues.
  - Create pull requests.
  - Fetch commits.
- **3. Interface**: Exposed as a **REST API** using FastAPI with auto-generated Swagger/Redoc documentation.
- **4. Tech Stack**: Built with **Python 3.10+** and **FastAPI**, following modern asynchronous patterns.
- **5. Code Quality**:
  - **Modularity**: Clearly separated routes, services, models, and core configuration.
  - **Error Handling**: Custom exception hierarchy and exponential backoff for API resilience.
  - **Testing**: Comprehensive test suite covering authentication flow and GitHub routes.

## Project Structure

```text
src/
├── auth/           # OAuth logic and routes
├── core/           # Configuration and logging
├── github/         # GitHub API client and business logic
├── models/         # Pydantic data models
└── dependencies/   # FastAPI dependency injection
```
