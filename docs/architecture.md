# System Architecture

The GitHub Connector is built as a modular FastAPI application, prioritizing scalability, resilience, and clear separation of concerns.

## 1. High-Level Architectural Layers

### API Layer (FastAPI)

Acts as the entry point for all requests. It handles routing, request validation via Pydantic models, and response serialization.

- **Authentication Routes**: Manage the OAuth2 flow (`/auth/github/login`, `/auth/github/callback`).
- **GitHub Routes**: Expose GitHub functionalities (repos, issues, etc.) under the `/github` prefix.

### Authentication Service (`src.auth`)

Orchestrates the OAuth2 handshake using `Authlib`.

- **Token Management**: Handles token exchange and revocation.
- **Session Handling**: Uses custom HTTP-only, secure cookies to store a `session_id`. The actual user state (including the GitHub `access_token`) is stored in an in-memory `SESSION_CACHE`.
- **Bearer Token Validation**: Actively validates incoming `Authorization: Bearer` tokens by resolving them against the GitHub API and caching the result in `TOKEN_CACHE`.

### GitHub Service Layer (`src.github`)

Contains the core business logic for interacting with GitHub, separating the low-level transport from the high-level API.

- **GitHub Client**: A low-level `httpx` based client that implements the "Resilient Client" pattern (retries, rate-limiting, pagination).
- **GitHub Service**: Orchestrates calls to the GitHub Client to perform specific actions.
- **Modular Routes**: Grouped by GitHub resources (Issues, Pulls, Repos, Commits) for maintainability.

### Core & Infrastructure (`src.core`)

Provides cross-cutting concerns:

- **Configuration**: Uses `pydantic-settings` for environment-based configuration.
- **Logging**: Implements structured logging with `structlog`.
- **Error Handling**: Global exception handlers in `app.py` translate internal errors into standardized JSON responses.

---

## 2. Detailed Component Breakdown

### Entry Point: `src/app.py`

The application is initialized here.

- **Middleware**: Includes `SessionMiddleware` specifically for **Authlib's internal OAuth state management** (e.g., storing the `state` parameter). It is **not** used for persisting user session data.
- **Global Error Handling**: Centralized handlers catch `ApiError` (and its subclasses like `AuthError`, `NotFoundError`, `RateLimitError`) and return consistent `ErrorResponse` models with appropriate HTTP status codes and headers (e.g., `Retry-After`).

### Core Configuration: `src/core/`

- **`config.py`**: Loads and validates environment variables.
- **`logging.py`**: Configures `structlog` for structured JSON logging.
- **`session.py`**: Defines `SESSION_CACHE` and `TOKEN_CACHE` for server-side state.

### Authentication Flow: `src/auth/`

- **`service.py` (`GitHubAuthService`)**: Generates login URLs, handles callbacks, and manages session lifecycle (create/delete).
- **`routes.py`**: Maps endpoints to service methods and manages response cookies.

### Dependency Injection: `src/dependencies/`

- **`auth.py`**: Resolves the current user from either a `user_session` cookie or an `Authorization: Bearer` header.
- **`github.py`**: Provides a unified `github_provider` factory that returns a fully configured `GitHubService` for the authenticated user.

### GitHub Client & Resilience: `src/github/`

- **`client.py` (`GitHubClient`)**: Handles raw HTTP communication, authentication headers, pagination, and rate limit monitoring.
- **`retry_policy.py` (`GitHubRetryPolicy`)**: Implements exponential backoff and determines retry eligibility for failed requests.
- **`service.py` (`GitHubService`)**: Provides a high-level API for the rest of the application (e.g., `get_repositories`, `create_issue`).

### Modular Routes: `src/github/routes/`

Endpoints are split into resource-specific files (e.g., `repos.py`, `issues.py`) to avoid massive route files and improve maintainability.

---

## 3. Data Flow

1. **User Login**: User initiates login $\to$ Redirected to GitHub $\to$ Returns to callback.
2. **Session established**: App generates a secure `session_id`, stores user data in `SESSION_CACHE`, and sets a `user_session` cookie on the client.
3. **API Request**:
    - **Session/Token Resolution**: User calls an endpoint $\to$ `github_provider` factory resolves the user (Cookie or Bearer).
    - **Service Injection**: `GitHubService` is initialized with a `GitHubClient` and injected into the route handler.
4. **Resilience**: If GitHub API returns 429 (Rate Limit) or 5xx, the client handles retries internally based on the `GitHubRetryPolicy`.
5. **Error Translation**: Any uncaught `ApiError` is swept up by the global exception handler in `app.py` and returned as a standardized JSON response.
