from typing import Optional

from pydantic import BaseModel


class LoginResponse(BaseModel):
    """Response model for login endpoint."""

    login_url: str


class CallbackResponse(BaseModel):
    """Response model for callback endpoint."""

    access_token: str
    token_type: str
    username: str
    expires_in: Optional[int] = None
    created_at: int


class UserResponse(BaseModel):
    """Response model for /me endpoint."""

    username: str
    created_at: int
    expires_at: Optional[int] = None
