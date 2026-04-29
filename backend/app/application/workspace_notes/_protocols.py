"""Protocol do WorkspaceNotesRepository — DIP (ADR-101)."""

from __future__ import annotations

from typing import Optional, Protocol

from backend.app.models.workspace_note import WorkspaceNotes


class WorkspaceNotesRepositoryProtocol(Protocol):
    async def get_by_id(self, workspace_id: str, note_id: str) -> Optional[WorkspaceNotes]: ...

    async def list_by_workspace(self, workspace_id: str) -> list[WorkspaceNotes]: ...

    async def add(self, note: WorkspaceNotes) -> WorkspaceNotes: ...

    async def delete(self, note: WorkspaceNotes) -> None: ...
