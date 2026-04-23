"""Use case: lista memberships do usuário logado (me-centric)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.workspace._dtos import (
    UserWorkspaceListResponse,
    UserWorkspaceResponse,
)
from backend.app.models.workspace import Workspace
from backend.app.models.workspace_member import WorkspaceMember


async def list_my_workspaces(user_id: str, *, db: AsyncSession) -> UserWorkspaceListResponse:
    # tenancy: global — auth-level listing of user's memberships
    stmt = (
        select(WorkspaceMember, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(WorkspaceMember.joined_at.asc())
    )
    rows = (await db.execute(stmt)).all()
    items = [
        UserWorkspaceResponse(
            id=ws.id,
            name=ws.name,
            family_surname=ws.family_surname,
            role=wm.role,  # type: ignore[arg-type]
            joined_at=wm.joined_at,
        )
        for wm, ws in rows
    ]
    return UserWorkspaceListResponse(workspaces=items, total=len(items))
