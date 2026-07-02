"""Auth router fino — register, login, refresh, logout, me (A6e.4 · ADR-072 · ADR-170).

``register`` / ``login`` delegam a :mod:`backend.app.application.auth`.
``ConflictError`` → 409, ``AuthenticationError`` → 401 via handlers globais.
``GET /me`` continua aqui pois depende de ``get_current_user`` (FastAPI
dependency já valida JWT e responde 401 antes do handler).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.auth import login_user, register_user
from backend.app.application.auth.login_user import access_token_ttl
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.security import create_access_token
from backend.app.models.user import User
from backend.app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    SessionTokens,
    TokenResponse,
    UserResponse,
)
from backend.app.services.rate_limit import client_ip_key, rate_limited
from backend.app.services.refresh_rate_limit import check_refresh_rate
from backend.app.services.refresh_token_service import (
    REFRESH_COOKIE_NAME,
    parse_refresh_cookie,
    revoke_family,
    revoke_family_by_cookie,
    rotate_refresh_token,
)
from backend.app.services.register_rate_limit import check_register_rate

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE_PATH_SUFFIX = "/auth"  # path real = API_PREFIX + sufixo (emenda ADR-170)


def _client_ip(request: Request) -> str | None:
    """Extrai IP da request, respeitando X-Forwarded-For (proxy do Coolify/Traefik)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _refresh_cookie_path() -> str:
    # Cobre /auth/refresh E /auth/logout; cookie não viaja para rotas de negócio.
    return f"{settings.API_PREFIX}{_REFRESH_COOKIE_PATH_SUFFIX}"


def _apply_session_cookies(response: Response, session: SessionTokens) -> None:
    """Set-Cookie do refresh (flag on) + no-store — token nunca é cacheável."""
    response.headers["Cache-Control"] = "no-store"
    if session.refresh_cookie is None or session.refresh_expires_at is None:
        return
    _set_refresh_cookie(response, session.refresh_cookie, session.refresh_expires_at)


def _set_refresh_cookie(response: Response, cookie_value: str, expires_at: datetime) -> None:
    max_age = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        cookie_value,
        max_age=max(max_age, 0),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax",
        path=_refresh_cookie_path(),
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=_refresh_cookie_path())


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    allowed, retry_after = check_register_rate(_client_ip(request))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many register attempts from this IP; try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    session = await register_user(body, db=db)
    _apply_session_cookies(response, session)
    return session


@router.post(
    "/login",
    response_model=TokenResponse,
    # W4-T04: per-IP — complementa o lockout per-conta do brute_force_lockout.
    dependencies=[rate_limited("login", key=client_ip_key)],
)
async def login(
    body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    session = await login_user(body, db=db)
    _apply_session_cookies(response, session)
    return session


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Rotaciona o refresh cookie e emite access novo (ADR-170 · W3-T03)."""
    cookie_value = _validate_refresh_request(request)
    _enforce_refresh_rate(request, cookie_value)
    return await _rotate_session(cookie_value, response, db)


def _validate_refresh_request(request: Request) -> str:
    """Guards do refresh: flag off → 404 (rota sempre montada, OpenAPI estável);
    header custom ``X-Refresh-Request`` é a defesa CSRF (form cross-origin não
    o seta sem preflight, que a allowlist CORS nega)."""
    if not settings.AUTH_REFRESH_FLOW:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if request.headers.get("x-refresh-request") != "1":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="missing X-Refresh-Request header"
        )
    cookie_value = request.cookies.get(REFRESH_COOKIE_NAME)
    if not cookie_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing refresh cookie"
        )
    return cookie_value


def _enforce_refresh_rate(request: Request, cookie_value: str) -> None:
    parsed = parse_refresh_cookie(cookie_value)
    family_id = parsed[0] if parsed else None
    allowed, retry_after = check_refresh_rate(_client_ip(request), family_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many refresh attempts; try again later.",
            headers={"Retry-After": str(retry_after)},
        )


async def _rotate_session(cookie_value: str, response: Response, db: AsyncSession) -> TokenResponse:
    response.headers["Cache-Control"] = "no-store"
    rotation = await rotate_refresh_token(db, cookie_value)
    if rotation is None:
        await db.commit()  # persiste revoke de reuse-detection
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        )
    user = await db.get(User, rotation.user_id)
    if user is None or not user.is_active or user.token_version != rotation.token_version_at_issue:
        # tv bump = forced logout (F9): mata a família, não só os access tokens.
        await revoke_family(db, rotation.family_id)
        await db.commit()
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        )
    await db.commit()
    if rotation.cookie_value is not None:
        _set_refresh_cookie(response, rotation.cookie_value, rotation.expires_at)
    token = create_access_token(
        subject=user.id, expires_delta=access_token_ttl(), token_version=user.token_version
    )
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    """Revoga a família do cookie (se houver) e limpa o cookie. Idempotente."""
    cookie_value = request.cookies.get(REFRESH_COOKIE_NAME)
    if cookie_value:
        await revoke_family_by_cookie(db, cookie_value)
        await db.commit()
    _clear_refresh_cookie(response)
    response.headers["Cache-Control"] = "no-store"


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
