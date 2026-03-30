# System Architecture

The GitHub Connector is built as a modular FastAPI application, prioritizing scalability, resilience, and clear separation of concerns.

## Architectural Layers

### 1. API Layer (FastAPI)

Acts as the entry point for all requests. It handles routing, request validation via Pydantic models, and response serialization.

- **Authentication Routes**: Manage the OAuth2 flow (`/auth/github/login`, `/auth/github/callback`).
- **GitHub Routes**: Expose GitHub functionalities (repos, issues, etc.) under the `/github` prefix.

### 2. Authentication Service (`src.auth`)

Orchestrates the OAuth2 handshake using `Authlib`.

- **Token Management**: Handles token exchange and revocation.
- **Session Handling**: Uses custom HTTP-only, secure cookies to store a `session_id`. The actual user state (including the GitHub `access_token`) is stored in an in-memory `SESSION_CACHE`.
- **Bearer Token Validation**: Actively validates incoming `Authorization: Bearer` tokens by resolving them against the GitHub API and caching the result in `TOKEN_CACHE`.

### 3. GitHub Service Layer (`src.github`)

Contains the core business logic for interacting with GitHub, separating the low-level transport from the high-level API.

- **GitHub Client**: A low-level `httpx` based client that implements the "Resilient Client" pattern (retries, rate-limiting, pagination).
- **GitHub Service**: Orchestrates calls to the GitHub Client to perform specific actions (list repos, create issues, etc.).
- **Modular Routes**: Grouped by GitHub resources (Issues, Pulls, Repos, Commits) for maintainability.

### 4. Core & Infrastructure (`src.core`)

Provides cross-cutting concerns:

- **Configuration**: Uses `pydantic-settings` for environment-based configuration and type safety.
- **Logging**: Implements structured logging with `structlog`.

### 5. Dependency Injection (`src.dependencies`)

Encapsulates service instantiation and authentication checks, making the API layer thin and testable.

## Data Flow

1. **User Login**: User initiates login $\to$ Redirected to GitHub $\to$ Returns to callback.
2. **Session established**: App generates a secure `session_id`, stores user data in `SESSION_CACHE`, and sets a `user_session` cookie on the client.
3. **API Request**:
    - **Cookie Auth**: User calls an endpoint $\to$ `get_session_user` retrieves data from `SESSION_CACHE`.
    - **Bearer Auth**: User provides a token $\to$ `get_optional_user` validates the token with GitHub (and `TOKEN_CACHE`) to resolve the username.
    - **Client/Service Init**: `GitHubClient` is initialized with the resolved token. `GitHubService` is initialized with the client $\to$ Request is made to GitHub API via the service.
4. **Resilience**: If GitHub API returns 429 (Rate Limit) or 5xx, the client handles retries internally before returning to the route handler.
