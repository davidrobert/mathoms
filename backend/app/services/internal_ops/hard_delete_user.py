"""Hard delete de usuário (ADR-116 Decisão 2).

**NUNCA é default.** Caller precisa fornecer `reason` (registrado no audit).
Deleta o registro `User`; CASCADEs cuidam de `workspaces`, `memberships` etc.
FKs com `ondelete="SET NULL"` (ex.: `pipeline_runs.triggered_by_user_id` se
houver) ficam NULL.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.services.internal_ops.audit import (
    AuditRecord,
    append_audit,
)
from backend.app.services.internal_ops.results import OpResult


async def hard_delete_user(
    db: AsyncSession, user_id: str, *, actor: str, reason: str
) -> OpResult:
    """Remove o usuário do banco. `reason` obrigatória, registrada no audit."""
    if not reason or not reason.strip():
        return OpResult.failure("reason_required", user_id=user_id)

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        return OpResult.failure("user_not_found", user_id=user_id)

    email = user.email
    await db.delete(user)
    await db.flush()

    append_audit(
        AuditRecord(
            action="user.hard_delete",
            actor=actor,
            target_type="user",
            target_id=user_id,
            result="ok",
            details={"email": email, "reason": reason.strip()},
        )
    )
    return OpResult.success(user_id=user_id)
