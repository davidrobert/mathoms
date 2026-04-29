"""Response DTOs do aggregate ``WorkspaceNotes`` (ADR-153)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WorkspaceNoteResponse(BaseModel):
    """Nota livre projetada para a UI."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    title: Optional[str] = None
    content: str
    pinned: bool
    author_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WorkspaceNoteListResponse(BaseModel):
    """Lista ordenada por ``pinned desc, updated_at desc``."""

    notes: list[WorkspaceNoteResponse]
    total: int
