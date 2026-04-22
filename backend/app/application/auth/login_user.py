"""Use case: valida credenciais e emite JWT."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base import AuthenticationError
from backend.app.core.security import create_access_token, verify_password
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, TokenResponse


async def login_user(body: LoginRequest, *, db: AsyncSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise AuthenticationError("Credenciais inválidas")

    token = create_access_token(subject=user.id, token_version=user.token_version)
    return TokenResponse(access_token=token)
