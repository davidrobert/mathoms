"""Use case: update role de um membro + emit AuditLogEvent."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.events import dispatch_sync
from backend.app.events.domain import AuditLogEvent
from backend.app.models.user import User
from backend.app.schemas.workspace_members import MemberResponse, MemberRoleUpdateRequest
from backend.app.services import membership_service
from backend.app.services.audit import client_meta


async def update_member_role(
    workspace_id: str,
    user_id: str,
    body: MemberRoleUpdateRequest,
    *,
    actor: User,
    request: Request,
    db: AsyncSession,
) -> MemberResponse:
    member = await membership_service.get_member(workspace_id, user_id, db=db)
    if member is None:
        raise NotFoundError("Membro não encontrado.")
    previous_role = member.role

    updated = await membership_service.update_member_role(
        workspace_id, user_id, new_role=body.role, db=db
    )

    ip, ua = client_meta(request)
    await dispatch_sync(
        AuditLogEvent(
            aggregate_id=updated.id,
            aggregate_type="workspace_member",
            workspace_id=workspace_id,
            action="workspace.member.role_change",
            resource_type="workspace_member",
            resource_id=updated.id,
            actor_user_id=actor.id,
            ip_address=ip,
            user_agent=ua,
            details={
                "target_user_id": user_id,
                "from_role": previous_role,
                "to_role": updated.role,
            },
        ),
        {"db": db},
    )
    await db.commit()
    await db.refresh(updated)

    # tenancy: global — re-fetch do user para formar MemberResponse completo
    u_row = await db.execute(select(User).where(User.id == user_id))
    user_obj = u_row.scalar_one()
    return MemberResponse(
        user_id=user_obj.id,
        email=user_obj.email,
        full_name=user_obj.full_name,
        role=updated.role,  # type: ignore[arg-type]
        joined_at=updated.joined_at,
        invited_by=updated.invited_by,
    )
