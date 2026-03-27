from typing import Any, Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standardized error response model."""

    type: str
    status: int
    details: Optional[Any] = None


class ApiError(Exception):
    """Base class for all API errors."""

    def __init__(self, status: int, type: str, details: Optional[Any] = None):
        self.status = status
        self.type = type
        self.details = details
        super().__init__(f"{type}: {status}")


class AuthError(ApiError):
    def __init__(self, status: int = 401, details: Optional[Any] = None):
        super().__init__(status, "auth", details)


class ValidationError(ApiError):
    def __init__(self, status: int = 422, details: Optional[Any] = None):
        super().__init__(status, "validation", details)


class NotFoundError(ApiError):
    def __init__(self, status: int = 404, details: Optional[Any] = None):
        super().__init__(status, "not_found", details)


class PermissionError(ApiError):
    def __init__(self, status: int = 403, details: Optional[Any] = None):
        super().__init__(status, "permission", details)


class RedirectError(ApiError):
    def __init__(self, status: int = 301, details: Optional[Any] = None):
        super().__init__(status, "redirect", details)


class ConflictError(ApiError):
    def __init__(self, status: int = 409, details: Optional[Any] = None):
        super().__init__(status, "conflict", details)


class RateLimitError(ApiError):
    def __init__(self, status: int = 429, retry_after: Optional[float] = None):
        self.retry_after = retry_after
        super().__init__(status, "rate_limit", {"retry_after": retry_after})


class ServerError(ApiError):
    def __init__(self, status: int = 500, details: Optional[Any] = None):
        super().__init__(status, "server", details)


class TimeoutError(ApiError):
    def __init__(self, status: int = 408, details: Optional[Any] = None):
        super().__init__(status, "timeout", details)


class NetworkError(ApiError):
    def __init__(self, details: Optional[Any] = None):
        super().__init__(503, "network", details)
