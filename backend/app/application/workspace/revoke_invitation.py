"""Use case: revoga convite pendente + audit (owner-only, idempotente)."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.services import audit_service, invitation_service


async def revoke_invitation(
    workspace_id: str,
    invitation_id: str,
    *,
    actor: User,
    request: Request,
    db: AsyncSession,
) -> None:
    inv = await invitation_service.revoke_invitation(workspace_id, invitation_id, db=db)
    await audit_service.log(
        db=db,
        workspace_id=workspace_id,
        action="workspace.member.revoke_invite",
        resource_type="workspace_invitation",
        resource_id=inv.id,
        actor_user_id=actor.id,
        details={"email": inv.email},
        request=request,
    )
    await db.commit()
