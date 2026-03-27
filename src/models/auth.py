from pydantic import BaseModel


class LoginResponse(BaseModel):
    """Response model for login endpoint."""

    login_url: str


class CallbackResponse(BaseModel):
    """Response model for callback endpoint."""

    access_token: str
    token_type: str
    username: str
