"""Login/logout do console interno."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.app.core.internal_ops_auth import (
    InternalOpsConfigError,
    InternalOpsPrincipal,
    create_session_token,
    load_operators,
    require_internal_operator,
    session_cookie_name,
    session_ttl_minutes,
    verify_operator_password,
)
from backend.app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminLogoutResponse,
    AdminPrincipalResponse,
)
from backend.app.services.internal_ops.audit import AuditRecord, append_audit

router = APIRouter()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=session_cookie_name(),
        value=token,
        max_age=session_ttl_minutes() * 60,
        path="/admin",
        httponly=True,
        samesite="strict",
        secure=False,  # IA-0 roda em 127.0.0.1; F7F-Remote flipa para True.
    )


@router.post("/login", response_model=AdminLoginResponse)
async def login(payload: AdminLoginRequest, response: Response) -> AdminLoginResponse:
    try:
        operators = load_operators()
    except InternalOpsConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    op = operators.get(payload.username)
    if op is None or not verify_operator_password(op, payload.password):
        append_audit(
            AuditRecord(
                action="ops.login_failed",
                actor=f"ops:{payload.username}",
                result="fail",
            )
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials"
        )

    principal = InternalOpsPrincipal(username=op.username, role=op.role)
    token = create_session_token(principal)
    _set_session_cookie(response, token)
    append_audit(
        AuditRecord(action="ops.login", actor=principal.actor, result="ok")
    )
    return AdminLoginResponse(
        username=principal.username,
        role=principal.role,
        expires_in_minutes=session_ttl_minutes(),
    )


@router.post("/logout", response_model=AdminLogoutResponse)
async def logout(
    response: Response,
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> AdminLogoutResponse:
    response.delete_cookie(key=session_cookie_name(), path="/admin")
    append_audit(AuditRecord(action="ops.logout", actor=principal.actor))
    return AdminLogoutResponse(ok=True)


@router.get("/me", response_model=AdminPrincipalResponse)
async def me(
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> AdminPrincipalResponse:
    return AdminPrincipalResponse(username=principal.username, role=principal.role)
