"""WorkspaceNotesRepository — persistência do aggregate ``WorkspaceNotes`` (ADR-153 · ADR-101 R13/R14)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workspace_note import WorkspaceNotes


class WorkspaceNotesRepository:
    """Single Responsibility: persistência de ``WorkspaceNotes``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, workspace_id: str, note_id: str) -> Optional[WorkspaceNotes]:
        result = await self._session.execute(
            select(WorkspaceNotes).where(
                WorkspaceNotes.workspace_id == workspace_id,
                WorkspaceNotes.id == note_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: str) -> list[WorkspaceNotes]:
        """Notas do workspace: pinned primeiro, depois mais recentes."""
        result = await self._session.execute(
            select(WorkspaceNotes)
            .where(WorkspaceNotes.workspace_id == workspace_id)
            .order_by(
                WorkspaceNotes.pinned.desc(),
                WorkspaceNotes.updated_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def add(self, note: WorkspaceNotes) -> WorkspaceNotes:
        self._session.add(note)
        await self._session.flush()
        return note

    async def delete(self, note: WorkspaceNotes) -> None:
        await self._session.delete(note)
        await self._session.flush()
