"""Reset de senha via console interno (ADR-116)."""

from __future__ import annotations

import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models.user import User
from backend.app.services.internal_ops.audit import AuditRecord, append_audit
from backend.app.services.internal_ops.results import OpResult

_ALPHABET = string.ascii_letters + string.digits + "!@#$%&*"


def generate_temp_password(length: int = 16) -> str:
    """Gera senha forte aleatória — retornada apenas no OpResult (one-time)."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


async def reset_password(
    db: AsyncSession,
    user_id: str,
    *,
    actor: str,
    new_password: str | None = None,
) -> OpResult:
    """Troca a senha do user e bumpa `token_version` (invalida sessões ativas).

    Se `new_password` não vier, gera uma senha temporária forte e devolve no
    `details["temp_password"]` (UI mostra one-time e descarta).
    """
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        return OpResult.failure("user_not_found", user_id=user_id)

    issued = new_password or generate_temp_password()
    user.hashed_password = hash_password(issued)
    user.token_version = (user.token_version or 0) + 1
    await db.flush()

    append_audit(
        AuditRecord(
            action="user.reset_password",
            actor=actor,
            target_type="user",
            target_id=user.id,
            details={"generated": new_password is None},
        ),
        db,
    )
    return OpResult.success(user_id=user.id, temp_password=issued)
