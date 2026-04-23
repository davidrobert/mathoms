"""Use case: cria convite + emit AuditLogEvent (owner-only)."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.workspace._dtos import invitation_to_response
from backend.app.events import dispatch_sync
from backend.app.events.domain import AuditLogEvent
from backend.app.models.user import User
from backend.app.schemas.workspace_members import (
    InvitationCreateRequest,
    InvitationCreateResponse,
)
from backend.app.services import invitation_service
from backend.app.services.audit import client_meta


async def create_invitation(
    workspace_id: str,
    body: InvitationCreateRequest,
    *,
    actor: User,
    request: Request,
    db: AsyncSession,
) -> InvitationCreateResponse:
    invitation, raw_token = await invitation_service.create_invitation(
        workspace_id,
        email=body.email,
        role=body.role,
        invited_by=actor.id,
        db=db,
    )
    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=invitation.id,
            aggregate_type="workspace_invitation",
            workspace_id=workspace_id,
            action="workspace.member.invite",
            resource_type="workspace_invitation",
            resource_id=invitation.id,
            actor_user_id=actor.id,
            ip_address=ip,
            user_agent=ua,
            details={"email": body.email, "role": body.role},
        ),
        {"db": db},
    )
    await db.commit()
    await db.refresh(invitation)
    return InvitationCreateResponse(
        invitation=invitation_to_response(invitation),
        token=raw_token,
        invite_path=f"/invite/{raw_token}",
    )
