# Design Decisions

This document outlines the key technical decisions made during the development of the GitHub Connector and the rationale behind them.

## 1. OAuth2 Implementation Strategy

### Decision: Secret session_id with In-Memory Session Cache

**Rationale**: Instead of storing the entire user state (including the GitHub `access_token`) in a JSON string cookie, we generate a cryptographically secure `session_id`.

- **Security**: Cookies with `httponly=True`, `secure=True`, and `samesite="lax"` prevent XSS-based token theft and eavesdropping.
- **Server Cache**: The `access_token` and user data are stored securely on the server in a dictionary (`SESSION_CACHE`), avoiding raw token exposure in the browser.
- **Bearer Validation**: Incoming Bearer tokens are actively validated using the GitHub API and cached in `TOKEN_CACHE` to avoid repeated calls while ensuring security.
- **Note**: GitHub OAuth tokens do not expire by default. Use `/logout` for revocation.

## 2. GitHub Client Resilience

### Decision: Exponential Backoff for Retries

**Rationale**: Network glitches and temporary GitHub outages are inevitable. The client implements a retry mechanism that increases the wait time between attempts (1s, 2s, 4s...) to avoid overwhelming the server during recovery.

### Decision: Proactive Rate Limit Handling

**Rationale**: GitHub's rate limits are strictly enforced.

- **Wait/Reset Extraction**: The client parses the `X-RateLimit-Reset` header.
- **Automated Wait**: Instead of failing immediately, the client can pause execution until the limit resets, providing a seamless experience for long-running batch operations.

## 3. Modular Route Structure

### Decision: Resource-based Route Splitting

**Rationale**: Instead of a single `routes.py`, we split routes into `repos.py`, `issues.py`, etc., within the `src/github/routes/` package.

- **Avoids Megafiles**: Keeps individual files under 200 lines.
- **Team Scalability**: Allows multiple developers to work on different GitHub features without merge conflicts.

## 4. Error Handling Strategy

### Decision: Custom Exception Hierarchy

**Rationale**: GitHub returns various error types. We map these to a custom hierarchy (e.g., `NotFoundError`, `RateLimitError`, `ValidationError`).

- **Standardization**: All GitHub-related errors are caught and re-raised as standard application errors.
- **API Consistency**: Routes can catch these specific errors and return standardized JSON responses to the client.

## 5. Structured Logging

### Decision: Using `structlog`

**Rationale**: Traditional string-based logging is hard to parse at scale. `structlog` allows us to log key-value pairs (e.g., `url`, `method`, `status_code`), making it easy to query logs in logs management tools.

---

## Scope and Skipped Items

To maintain the project's focus as a "simple cloud connector", the following items were intentionally skipped for now:

### 1. Persistent Database

- **Status**: Limited (In-Memory).
- **Rationale**: User sessions and OAuth states are managed through secret session IDs and memory-based caches (`SESSION_CACHE`, `TOKEN_CACHE`). Introducing a full-featured database (e.g., PostgreSQL/Redis) would add significant deployment complexity. For current scale, in-memory structures are sufficient, with clear "TODO" markers for when persistent storage becomes necessary.

### 2. Frontend Application

- **Status**: Skipped.
- **Rationale**: The project focus is strictly on the Backend API. While the API supports a full OAuth flow, it is designed to be used by a separate frontend or consumed directly via tools like Postman or the built-in Swagger UI.

### 3. GitHub Webhooks Integration

- **Status**: Skipped.
- **Rationale**: Webhooks require a public, internet-accessible URL to receive payloads. Setting up local tunnels or public staging environments was deemed out of scope for a local development demonstration.

### 4. Advanced User Management

- **Status**: Skipped.
- **Rationale**: We focus on a "single-session" model where the authenticated user interacts with their own GitHub resources. A full user profile system with roles and permissions was not required for the connector's objective.
