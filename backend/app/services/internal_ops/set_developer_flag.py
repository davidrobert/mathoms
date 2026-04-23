"""Toggle do flag `is_developer` (7F.15 · ADR-116).

Mutação sensível: bumpa `token_version` para invalidar JWTs cacheados
que carregam claim `is_developer`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult


async def set_developer_flag(
    db: AsyncSession, user_id: str, *, enabled: bool, actor: str
) -> OpResult:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        return OpResult.failure("user_not_found", user_id=user_id)

    previous = bool(user.is_developer)
    if previous == enabled:
        return OpResult.success(user_id=user.id, changed=False, is_developer=enabled)

    user.is_developer = enabled
    user.token_version = (user.token_version or 0) + 1
    await db.flush()

    append_audit(
        AuditRecord(
            action="user.set_developer_flag",
            actor=actor,
            target_type="user",
            target_id=user.id,
            details={"previous": previous, "current": enabled},
        )
    )
    return OpResult.success(user_id=user.id, changed=True, is_developer=enabled)
