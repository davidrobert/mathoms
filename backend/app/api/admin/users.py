"""CRUD sensível de usuários via console interno."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.internal_ops_auth import (
    InternalOpsPrincipal,
    require_internal_operator,
)
from backend.app.models.user import User
from backend.app.schemas.admin import (
    AdminUserListResponse,
    AdminUserSummary,
    AnonymizeUserRequest,
    AnonymizeUserResponse,
    HardDeleteUserRequest,
    HardDeleteUserResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SetDeveloperFlagRequest,
    SetDeveloperFlagResponse,
    UpdateUserEmailRequest,
    UpdateUserEmailResponse,
    UpdateUserProfileRequest,
    UpdateUserProfileResponse,
)
from backend.app.services.internal_ops import (
    anonymize_user,
    hard_delete_user,
    reset_password,
    set_developer_flag,
    update_user_email,
    update_user_profile,
)

router = APIRouter(prefix="/users")


_ERROR_STATUS = {
    "user_not_found": status.HTTP_404_NOT_FOUND,
    "email_taken": status.HTTP_409_CONFLICT,
    "invalid_email": 422,
    "invalid_full_name": 422,
    "reason_required": 422,
}


def _raise_from(result) -> None:
    http_status = _ERROR_STATUS.get(result.error or "", status.HTTP_400_BAD_REQUEST)
    raise HTTPException(status_code=http_status, detail=result.error)


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    q: str | None = Query(default=None, description="Filtra por email ou nome"),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> AdminUserListResponse:
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(User.email).like(like) | func.lower(User.full_name).like(like))
    users = list((await db.execute(stmt.limit(limit))).scalars().all())
    total = int((await db.execute(select(func.count()).select_from(User))).scalar_one() or 0)
    return AdminUserListResponse(
        users=[AdminUserSummary.model_validate(u) for u in users], total=total
    )


@router.post("/{user_id}/anonymize", response_model=AnonymizeUserResponse)
async def anonymize(
    user_id: str,
    _body: AnonymizeUserRequest,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> AnonymizeUserResponse:
    result = await anonymize_user(db, user_id, actor=principal.actor)
    if not result.ok:
        _raise_from(result)
    await db.commit()
    return AnonymizeUserResponse(
        user_id=result.details["user_id"],
        anonymized_email=result.details["anonymized_email"],
    )


@router.post("/{user_id}/hard-delete", response_model=HardDeleteUserResponse)
async def hard_delete(
    user_id: str,
    body: HardDeleteUserRequest,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> HardDeleteUserResponse:
    if principal.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="superadmin_required")
    result = await hard_delete_user(db, user_id, actor=principal.actor, reason=body.reason)
    if not result.ok:
        _raise_from(result)
    await db.commit()
    return HardDeleteUserResponse(user_id=result.details["user_id"])


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_pw(
    user_id: str,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> ResetPasswordResponse:
    result = await reset_password(
        db, user_id, actor=principal.actor, new_password=body.new_password
    )
    if not result.ok:
        _raise_from(result)
    await db.commit()
    return ResetPasswordResponse(
        user_id=result.details["user_id"], temp_password=result.details["temp_password"]
    )


@router.post("/{user_id}/developer-flag", response_model=SetDeveloperFlagResponse)
async def set_dev_flag(
    user_id: str,
    body: SetDeveloperFlagRequest,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> SetDeveloperFlagResponse:
    result = await set_developer_flag(db, user_id, enabled=body.enabled, actor=principal.actor)
    if not result.ok:
        _raise_from(result)
    await db.commit()
    return SetDeveloperFlagResponse(
        user_id=result.details["user_id"],
        is_developer=result.details["is_developer"],
        changed=result.details["changed"],
    )


@router.patch("/{user_id}/email", response_model=UpdateUserEmailResponse)
async def patch_email(
    user_id: str,
    body: UpdateUserEmailRequest,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> UpdateUserEmailResponse:
    result = await update_user_email(
        db, user_id, new_email=str(body.new_email), actor=principal.actor
    )
    if not result.ok:
        _raise_from(result)
    await db.commit()
    return UpdateUserEmailResponse(
        user_id=result.details["user_id"],
        email=result.details["email"],
        changed=result.details["changed"],
    )


@router.patch("/{user_id}/profile", response_model=UpdateUserProfileResponse)
async def patch_profile(
    user_id: str,
    body: UpdateUserProfileRequest,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> UpdateUserProfileResponse:
    result = await update_user_profile(
        db,
        user_id,
        actor=principal.actor,
        full_name=body.full_name,
        is_active=body.is_active,
    )
    if not result.ok:
        _raise_from(result)
    await db.commit()
    return UpdateUserProfileResponse(
        user_id=result.details["user_id"],
        changed=result.details["changed"],
        fields=list(result.details.get("fields", [])),
    )
