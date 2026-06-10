"""Auth request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SessionTokens(TokenResponse):
    """Resultado interno de login/register (ADR-170). Os campos de refresh
    nunca saem no body — ``response_model=TokenResponse`` filtra; o router
    usa para emitir o Set-Cookie httpOnly."""

    refresh_cookie: Optional[str] = None
    refresh_expires_at: Optional[datetime] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_developer: bool = False

    model_config = {"from_attributes": True}
