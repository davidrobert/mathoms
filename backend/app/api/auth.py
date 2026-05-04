"""Auth router fino — register, login, me (A6e.4 · ADR-072 · ADR-101 R15/R16).

``register`` / ``login`` delegam a :mod:`backend.app.application.auth`.
``ConflictError`` → 409, ``AuthenticationError`` → 401 via handlers globais.
``GET /me`` continua aqui pois depende de ``get_current_user`` (FastAPI
dependency já valida JWT e responde 401 antes do handler).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.auth import login_user, register_user
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.services.register_rate_limit import check_register_rate

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    """Extrai IP da request, respeitando X-Forwarded-For (proxy do Coolify/Traefik)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    allowed, retry_after = check_register_rate(_client_ip(request))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many register attempts from this IP; try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    return await register_user(body, db=db)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await login_user(body, db=db)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
