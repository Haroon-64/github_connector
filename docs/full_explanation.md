# Code Explanation

The `github_connector` is a FastAPI application that interfaces with the GitHub API. It manages OAuth2 authentication, session handling, rate limiting, and pagination.

## 1. Entry Point: `app.py`

The application is initialized in `src/app.py` using FastAPI.

* **Middleware**: Includes `SessionMiddleware` specifically for **Authlib's internal OAuth state management** (e.g., storing the `state` parameter to prevent CSRF during the login handshake). It is intentionally **not** used for persisting user session data; that is handled manually via `session_id` and `SESSION_CACHE`.
* **Routers**: Registers `auth_router` and `github_router`.
* **Error Handling**: Converts internal exceptions into structured JSON responses.

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
  * Callback endpoint processes the OAuth response, generates a secure `session_id`, and stores the user data in `SESSION_CACHE`. It sets an HTTP-only, secure `user_session` cookie containing the ID.
  * Logout endpoint revokes the token with GitHub and deletes the session from `SESSION_CACHE`.

## 4. Dependency Injection Layer (`src/dependencies/`)

Uses FastAPI’s dependency system to supply authenticated context to routes.

* **`auth.py` and `github.py`**:
  * `get_session_user`: Validates the `user_session` cookie against `SESSION_CACHE`.
  * `get_optional_user`: Handles both session-based auth and `Authorization: Bearer` headers. Bearer tokens are dynamically validated via a call to GitHub's `/user`.
  * Provides a configured `GitHubService` (backed by a `GitHubClient`) to route handlers.

## 5. GitHub Service and Client (`src/github/`)

Handles API communication and related concerns.

* **`client.py` (`GitHubClient`)**:

  * Uses `httpx.AsyncClient` for HTTP requests.
  * **Transport Layer**: Handles the raw communication, authentication headers, and session management.
  * **Pagination**: Detects `Link` headers and retrieves all pages automatically.
  * **Rate Limiting**: Monitors rate limit headers and delays requests when necessary.
  * **Error Mapping**: Converts HTTP errors into internal exceptions such as `NotFoundError`, `PermissionError`, and `AuthError`.
* **`service.py` (`GitHubService`)**:

  * **Business Logic Layer**: Orchestrates calls to the GitHub Client.
  * Defines high-level methods: `get_repositories`, `get_user`, `create_issue`, `create_pull_request`, `get_commits`.
* **`retry_policy.py` (`GitHubRetryPolicy`)**:

  * Determines whether failed requests should be retried.
  * Applies exponential backoff with jitter for retry timing.

## 6. GitHub Routes (`src/github/routes/`)

Defines API endpoints that map to GitHub operations.

* Example: `commits.py` handles `/repos/{owner}/{repo}/commits`. It receives a `GitHubClient` via dependency injection, calls `client.get_commits`, and translates exceptions into HTTP responses.
