"""Lista workspaces de um usuário (owner + membro) — F7F-Local · ADR-116.

Read-only. Usada pelo console interno para mostrar os workspace_ids de um
user em expansão de linha, destravando o fluxo de purge/filtro de
relatórios por workspace.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workspace import Workspace
from backend.app.models.workspace_member import WorkspaceMember


@dataclass(frozen=True)
class UserWorkspaceSummary:
    id: str
    name: str
    role: str  # "owner" ou role do WorkspaceMember (admin/member/viewer…)
    created_at: datetime


async def list_user_workspaces(db: AsyncSession, user_id: str) -> list[UserWorkspaceSummary]:
    """Retorna workspaces em que o usuário é owner OU membro, ordenados por data."""
    owned_rows = (
        (
            await db.execute(
                select(Workspace)
                .where(Workspace.owner_id == user_id)
                .order_by(Workspace.created_at)
            )
        )
        .scalars()
        .all()
    )

    member_rows = (
        await db.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at)
        )
    ).all()

    seen: set[str] = set()
    out: list[UserWorkspaceSummary] = []
    for ws in owned_rows:
        if ws.id in seen:
            continue
        seen.add(ws.id)
        out.append(
            UserWorkspaceSummary(id=ws.id, name=ws.name, role="owner", created_at=ws.created_at)
        )
    for ws, role in member_rows:
        if ws.id in seen:
            continue
        seen.add(ws.id)
        out.append(
            UserWorkspaceSummary(id=ws.id, name=ws.name, role=role, created_at=ws.created_at)
        )
    return out
