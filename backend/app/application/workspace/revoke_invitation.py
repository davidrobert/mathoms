"""Use case: revoga convite pendente + emit AuditLogEvent (owner-only, idempotente)."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.events import dispatch_sync
from backend.app.events.domain import AuditLogEvent
from backend.app.models.user import User
from backend.app.services import invitation_service
from backend.app.services.audit import client_meta


async def revoke_invitation(
    workspace_id: str,
    invitation_id: str,
    *,
    actor: User,
    request: Request,
    db: AsyncSession,
) -> None:
    inv = await invitation_service.revoke_invitation(workspace_id, invitation_id, db=db)
    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=inv.id,
            aggregate_type="workspace_invitation",
            workspace_id=workspace_id,
            action="workspace.member.revoke_invite",
            resource_type="workspace_invitation",
            resource_id=inv.id,
            actor_user_id=actor.id,
            ip_address=ip,
            user_agent=ua,
            details={"email": inv.email},
        ),
        {"db": db},
    )
    await db.commit()
