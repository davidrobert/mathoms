"""Atualização de campos não-sensíveis de cadastro (7F.16 · ADR-116).

`full_name` e `is_active`. Email tem fluxo próprio em `update_user_email`
(sensível, bumpa `token_version`).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult


async def update_user_profile(
    db: AsyncSession,
    user_id: str,
    *,
    actor: str,
    full_name: str | None = None,
    is_active: bool | None = None,
) -> OpResult:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        return OpResult.failure("user_not_found", user_id=user_id)

    changes: dict[str, tuple[object, object]] = {}

    if full_name is not None:
        trimmed = full_name.strip()
        if not trimmed:
            return OpResult.failure("invalid_full_name", user_id=user_id)
        if user.full_name != trimmed:
            changes["full_name"] = (user.full_name, trimmed)
            user.full_name = trimmed

    if is_active is not None and bool(user.is_active) != bool(is_active):
        changes["is_active"] = (user.is_active, is_active)
        user.is_active = is_active

    if not changes:
        return OpResult.success(user_id=user.id, changed=False)

    await db.flush()
    append_audit(
        AuditRecord(
            action="user.update_profile",
            actor=actor,
            target_type="user",
            target_id=user.id,
            details={k: {"previous": v[0], "current": v[1]} for k, v in changes.items()},
        ),
        db,
    )
    return OpResult.success(user_id=user.id, changed=True, fields=list(changes.keys()))
