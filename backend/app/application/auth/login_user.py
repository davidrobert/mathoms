"""Use case: valida credenciais e emite JWT — com brute-force lockout (7B.13)."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base import AccountLockedError, AuthenticationError
from backend.app.core.config import settings
from backend.app.core.security import create_access_token, verify_password
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, SessionTokens
from backend.app.services.refresh_token_service import issue_refresh_family
from backend.app.services.security.brute_force_lockout import (
    BruteForceLockoutService,
    LockoutState,
    NoOpBruteForceLockoutService,
    get_default_lockout_service,
)

LockoutService = Union[BruteForceLockoutService, NoOpBruteForceLockoutService]


def access_token_ttl() -> Optional[timedelta]:
    """ADR-170: 15min com refresh flow on; None = default 24h (ADR-057 legado)."""
    if settings.AUTH_REFRESH_FLOW:
        return timedelta(minutes=settings.AUTH_REFRESH_ACCESS_TTL_MINUTES)
    return None


async def issue_session_tokens(user: User, *, db: AsyncSession) -> SessionTokens:
    """Access JWT + (flag on) família de refresh nova. Comita a família."""
    token = create_access_token(
        subject=user.id,
        expires_delta=access_token_ttl(),
        token_version=user.token_version,
    )
    if not settings.AUTH_REFRESH_FLOW:
        return SessionTokens(access_token=token)
    cookie_value, expires_at = await issue_refresh_family(
        db, user.id, token_version=user.token_version
    )
    await db.commit()
    return SessionTokens(
        access_token=token, refresh_cookie=cookie_value, refresh_expires_at=expires_at
    )


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
) -> SessionTokens:
    """Login com proteção brute-force (7B.13) + refresh family (ADR-170)."""
    if lockout is None:
        lockout = get_default_lockout_service()
    pre = lockout.check_locked(body.email)
    if pre.locked:
        _raise_locked(pre)
    user = await _authenticate_or_raise(db, body.email, body.password, lockout)
    lockout.record_success(body.email)
    return await issue_session_tokens(user, db=db)
