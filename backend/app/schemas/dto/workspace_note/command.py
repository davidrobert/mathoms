"""Command DTOs do aggregate ``WorkspaceNotes`` (ADR-153)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceNoteCreateCommand(BaseModel):
    """Cria nova nota livre no workspace."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=200)
    content: str = Field("", max_length=20_000)
    pinned: bool = False


class WorkspaceNoteUpdateCommand(BaseModel):
    """Atualiza title/content/pinned. Campos omitidos preservam valor atual."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, max_length=20_000)
    pinned: Optional[bool] = None
