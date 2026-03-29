# Code Explanation

The `github_connector` is a FastAPI application that interfaces with the GitHub API. It manages OAuth2 authentication, session handling, rate limiting, and pagination.

## 1. Entry Point: `app.py`

The application is initialized in `src/app.py` using FastAPI.

* **Middleware**: Adds `SessionMiddleware` configured with `OAUTH_SECRET`. A separate `user_session` cookie is used for primary state handling.
* **Routers**: Registers two routers: `auth_router` for authentication and `github_router` for GitHub operations.
* **Error Handling**: A global handler for `ApiError` converts internal exceptions (e.g., `NotFoundError`, `RateLimitError`) into structured JSON responses with appropriate HTTP status codes.

## 2. Core Configuration (`src/core/`)

* **`config.py`**: Uses `pydantic-settings` to load and validate environment variables such as `GITHUB_CLIENT_ID`, `OAUTH_SECRET`, and `GITHUB_API_URL`.
* **`logging.py`**: Configures `structlog` for structured JSON logging.
* **`constants.py`**: Defines static values such as `GITHUB_SCOPES`.

## 3. Authentication Flow (`src/auth/`)

Authentication is implemented with `Authlib` and maintains minimal server-side state.

* **`github.py` (`GitHubAuthService`)**:

  * `get_login_url`: Generates the GitHub authorization URL.
  * `handle_callback`: Exchanges the authorization code for an access token and retrieves user data.
  * `revoke_token`: Sends a request to invalidate the OAuth token.
* **`routes.py`**:

  * Login endpoint returns the authorization URL.
  * Callback endpoint processes the OAuth response and stores user data and token in an HTTP-only `user_session` cookie.

## 4. Dependency Injection Layer (`src/dependencies/`)

Uses FastAPI’s dependency system to supply authenticated context to routes.

* **`auth.py` and `github.py`**: Read and validate the `user_session` cookie, then provide a configured `GitHubClient` or user object to route handlers.

## 5. GitHub Service and Client (`src/github/`)

Handles API communication and related concerns.

* **`client.py` (`GitHubClient`)**:

  * Uses `httpx.AsyncClient` for HTTP requests.
  * **Pagination**: Detects `Link` headers and retrieves all pages automatically.
  * **Rate Limiting**: Monitors rate limit headers and delays requests when necessary.
  * **Error Mapping**: Converts HTTP errors into internal exceptions such as `NotFoundError`, `PermissionError`, and `AuthError`.
* **`retry_policy.py` (`GitHubRetryPolicy`)**:

  * Determines whether failed requests should be retried.
  * Applies exponential backoff with jitter for retry timing.

## 6. GitHub Routes (`src/github/routes/`)

Defines API endpoints that map to GitHub operations.

* Example: `commits.py` handles `/repos/{owner}/{repo}/commits`. It receives a `GitHubClient` via dependency injection, calls `client.get_commits`, and translates exceptions into HTTP responses.
