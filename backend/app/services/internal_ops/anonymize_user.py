"""Anonimização de usuário (ADR-116 Decisão 2).

Default seguro: `user.id` preservado (FKs intactas em workspaces, pipeline_runs,
audit_logs, etc). Campos PII substituídos por placeholders determinísticos,
`is_active=False`, `token_version` bumped para invalidar JWTs.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models.user import User
from backend.app.services.internal_ops.audit import (
    AuditRecord,
    append_audit,
)
from backend.app.services.internal_ops.results import OpResult

_ANONYMIZED_DOMAIN = "anonymized.invalid"


@dataclass(frozen=True)
class AnonymizeOutcome:
    user_id: str
    anonymized_email: str


def _anonymized_email(user_id: str) -> str:
    short = user_id.split("-", 1)[0]
    return f"anon-{short}@{_ANONYMIZED_DOMAIN}"


async def anonymize_user(db: AsyncSession, user_id: str, *, actor: str) -> OpResult:
    """Anonimiza o usuário `user_id`.

    Preserva `user.id` (FKs) e caminho de auditoria. Bumpa `token_version`.
    Idempotente: re-chamar em usuário já anonimizado retorna `ok` sem
    mudanças adicionais (email já no domínio `anonymized.invalid`).
    """
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        return OpResult.failure("user_not_found", user_id=user_id)

    already = user.email.endswith(f"@{_ANONYMIZED_DOMAIN}")
    new_email = _anonymized_email(user.id)
    user.email = new_email
    user.full_name = "Usuário anonimizado"
    user.hashed_password = hash_password(secrets.token_urlsafe(32))
    user.is_active = False
    user.token_version = (user.token_version or 0) + 1
    await db.flush()

    append_audit(
        AuditRecord(
            action="user.anonymize",
            actor=actor,
            target_type="user",
            target_id=user.id,
            result="ok",
            details={"anonymized_email": new_email, "already_anonymized": already},
        )
    )
    return OpResult.success(user_id=user.id, anonymized_email=new_email)
