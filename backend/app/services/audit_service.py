"""Audit service — thin wrapper para registrar eventos sensíveis no
`audit_logs` já existente (F6.5).

Filosofia:

- **Não há undo.** Uma entrada no audit log é imutável. Caller passa só
  o que aconteceu; service persiste + flush.
- **Não faz commit.** O caller decide o transaction boundary. Se o audit
  log e a mutação precisam ser atômicos (quase sempre), ficam no mesmo
  `db.commit()`.
- **Tenancy local.** Audit logs SEMPRE têm `workspace_id` (exceto em
  eventos pré-login como `auth.register` — que usamos raramente aqui).

## Convenção de actions para F9 (workspace sharing)

    workspace.member.invite          → convite criado
    workspace.member.accept          → convidado aceitou → novo member
    workspace.member.revoke_invite   → convite revogado antes do aceite
    workspace.member.role_change     → role de um member alterada
    workspace.member.remove          → member removido do workspace
    workspace.update                 → metadados do workspace editados

## Convenção de `details`

JSON livre, mas com campos sugeridos por action:

    invite          → {"email": "...", "role": "...", "invitation_id": "..."}
    accept          → {"invitation_id": "...", "role": "..."}
    revoke_invite   → {"invitation_id": "...", "email": "..."}
    role_change     → {"target_user_id": "...", "from_role": "...", "to_role": "..."}
    remove          → {"target_user_id": "...", "role": "..."}

Evite colocar PII que já está em outras tabelas (full_name, CPF, valores
monetários). Emails e IDs são ok.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog


async def log(
    *,
    db: AsyncSession,
    workspace_id: str,
    action: str,
    resource_type: str,
    actor_user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Grava uma entrada no audit log. Não commita — caller decide.

    Quando passado `request`, extrai IP e user-agent automaticamente. O
    IP é armazenado em texto cru (IPv4/IPv6), não hasheado: é auditoria
    interna, não analytics externo.
    """
    ip = None
    user_agent = None
    if request is not None:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    entry = AuditLog(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip,
        user_agent=user_agent,
    )
    db.add(entry)
    await db.flush()
    return entry


__all__ = ["log"]
