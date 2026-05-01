"""Use case: valida credenciais e emite JWT — com brute-force lockout (7B.13)."""

from __future__ import annotations

from typing import Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base import AccountLockedError, AuthenticationError
from backend.app.core.security import create_access_token, verify_password
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, TokenResponse
from backend.app.services.brute_force_lockout import (
    BruteForceLockoutService,
    LockoutState,
    NoOpBruteForceLockoutService,
    get_default_lockout_service,
)

LockoutService = Union[BruteForceLockoutService, NoOpBruteForceLockoutService]


def _raise_locked(state: LockoutState) -> None:
    raise AccountLockedError(
        f"Conta bloqueada por excesso de tentativas. Tente novamente em {state.retry_after_s}s.",
        retry_after_s=state.retry_after_s,
    )


async def _authenticate_or_raise(
    db: AsyncSession, email: str, password: str, lockout: LockoutService
) -> User:
    """Retorna User ou raise (Auth/AccountLocked) — encapsula contagem de falhas."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    post = lockout.record_failure(email)
    if post.locked:
        _raise_locked(post)
    raise AuthenticationError("Credenciais inválidas")


async def login_user(
    body: LoginRequest,
    *,
    db: AsyncSession,
    lockout: Optional[LockoutService] = None,
) -> TokenResponse:
    """Login com proteção brute-force (7B.13)."""
    if lockout is None:
        lockout = get_default_lockout_service()
    pre = lockout.check_locked(body.email)
    if pre.locked:
        _raise_locked(pre)
    user = await _authenticate_or_raise(db, body.email, body.password, lockout)
    lockout.record_success(body.email)
    token = create_access_token(subject=user.id, token_version=user.token_version)
    return TokenResponse(access_token=token)
