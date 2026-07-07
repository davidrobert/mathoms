"""Atualização de email (7F.16 · ADR-116).

Mutação sensível: email é identidade — mudar invalida JWTs existentes via
bump de `token_version` e exige unicidade (409 se colidir).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult


async def update_user_email(
    db: AsyncSession, user_id: str, *, new_email: str, actor: str
) -> OpResult:
    normalized = (new_email or "").strip().lower()
    if "@" not in normalized:
        return OpResult.failure("invalid_email", user_id=user_id)

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        return OpResult.failure("user_not_found", user_id=user_id)

    if user.email == normalized:
        return OpResult.success(user_id=user.id, changed=False, email=normalized)

    collision = (
        await db.execute(select(User).where(User.email == normalized, User.id != user_id))
    ).scalar_one_or_none()
    if collision is not None:
        return OpResult.failure("email_taken", user_id=user_id)

    previous = user.email
    user.email = normalized
    user.token_version = (user.token_version or 0) + 1
    await db.flush()

    # audit name dedicado (`user.email_changed`) facilita filtro no sink:
    # mudança de identidade é evento mais sensível que patch de perfil.
    append_audit(
        AuditRecord(
            action="user.email_changed",
            actor=actor,
            target_type="user",
            target_id=user.id,
            details={"old": previous, "new": normalized},
        ),
        db,
    )
    return OpResult.success(user_id=user.id, changed=True, email=normalized)
