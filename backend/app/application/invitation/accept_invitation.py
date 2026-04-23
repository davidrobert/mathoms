"""Use case: aceite de convite + emissão de AuditLogEvent."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.events import dispatch_sync
from backend.app.events.domain import AuditLogEvent
from backend.app.models.user import User
from backend.app.schemas.workspace_members import InvitationAcceptResponse
from backend.app.services import invitation_service
from backend.app.services.audit import client_meta


async def accept_invitation(
    token: str,
    *,
    user: User,
    request: Request,
    db: AsyncSession,
) -> InvitationAcceptResponse:
    member = await invitation_service.accept_invitation(token, acceptor=user, db=db)
    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=member.id,
            aggregate_type="workspace_member",
            workspace_id=member.workspace_id,
            action="workspace.member.accept",
            resource_type="workspace_member",
            resource_id=member.id,
            actor_user_id=user.id,
            ip_address=ip,
            user_agent=ua,
            details={"role": member.role},
        ),
        {"db": db},
    )
    await db.commit()
    await db.refresh(member)
    return InvitationAcceptResponse(
        workspace_id=member.workspace_id,
        role=member.role,  # type: ignore[arg-type]
        joined_at=member.joined_at,
    )
