"""Use case: cria convite + audit (owner-only)."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.workspace._dtos import invitation_to_response
from backend.app.models.user import User
from backend.app.schemas.workspace_members import (
    InvitationCreateRequest,
    InvitationCreateResponse,
)
from backend.app.services import audit_service, invitation_service


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
    await audit_service.log(
        db=db,
        workspace_id=workspace_id,
        action="workspace.member.invite",
        resource_type="workspace_invitation",
        resource_id=invitation.id,
        actor_user_id=actor.id,
        details={"email": body.email, "role": body.role},
        request=request,
    )
    await db.commit()
    await db.refresh(invitation)
    return InvitationCreateResponse(
        invitation=invitation_to_response(invitation),
        token=raw_token,
        invite_path=f"/invite/{raw_token}",
    )
