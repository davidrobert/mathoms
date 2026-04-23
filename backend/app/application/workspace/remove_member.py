"""Use case: remove membro + audit."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.services import audit_service, membership_service


async def remove_member(
    workspace_id: str,
    user_id: str,
    *,
    actor: User,
    request: Request,
    db: AsyncSession,
) -> None:
    removed = await membership_service.remove_member(workspace_id, user_id, db=db)
    await audit_service.log(
        db=db,
        workspace_id=workspace_id,
        action="workspace.member.remove",
        resource_type="workspace_member",
        resource_id=removed.id,
        actor_user_id=actor.id,
        details={"target_user_id": user_id, "role": removed.role},
        request=request,
    )
    await db.commit()
