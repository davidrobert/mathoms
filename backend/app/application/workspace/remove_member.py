"""Use case: remove membro + emit AuditLogEvent."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.events import dispatch_sync
from backend.app.events.domain import AuditLogEvent
from backend.app.models.user import User
from backend.app.services import membership_service
from backend.app.services.audit import client_meta


async def remove_member(
    workspace_id: str,
    user_id: str,
    *,
    actor: User,
    request: Request,
    db: AsyncSession,
) -> None:
    removed = await membership_service.remove_member(workspace_id, user_id, db=db)
    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=removed.id,
            aggregate_type="workspace_member",
            workspace_id=workspace_id,
            action="workspace.member.remove",
            resource_type="workspace_member",
            resource_id=removed.id,
            actor_user_id=actor.id,
            ip_address=ip,
            user_agent=ua,
            details={"target_user_id": user_id, "role": removed.role},
        ),
        {"db": db},
    )
    await db.commit()
