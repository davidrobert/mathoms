"""DTOs do sub-agregado ``TaskSuggestion`` (ADR-074).

Workflow: pending → approved (materializa Task) / rejected / merged
(anexa a Task existente). O payload proposto tem shape de ``TaskCreate``
exceto pelo ``number`` (importer-only).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.dto.task.response import TaskBase
from backend.app.schemas.dto.task.types import (
    SuggestionSource,
    SuggestionStatus,
)


class TaskSuggestionProposed(TaskBase):
    """Shape do payload proposto pela LLM.

    Idêntico a ``TaskCreateCommand`` exceto por não aceitar ``number``
    (importer-only).
    """

    pass


class TaskSuggestionCreateCommand(BaseModel):
    """``POST /task-suggestions`` — chamado pelo E5.N (ADR-074)."""

    proposed_payload: TaskSuggestionProposed
    source: SuggestionSource
    source_run_id: Optional[str] = None


class TaskSuggestionApproveCommand(BaseModel):
    """``POST /task-suggestions/{id}/approve``.

    ``edited_payload`` permite o usuário ajustar os campos antes de
    aceitar — se fornecido, sobrescreve ``proposed_payload`` ao
    materializar a Task.
    """

    edited_payload: Optional[TaskSuggestionProposed] = None


class TaskSuggestionRejectCommand(BaseModel):
    """``POST /task-suggestions/{id}/reject``."""

    reason: Optional[str] = Field(None, max_length=1000)


class TaskSuggestionResponse(BaseModel):
    """Sugestão persistida."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    proposed_payload: dict
    source: SuggestionSource
    source_run_id: Optional[str] = None
    status: SuggestionStatus
    rejection_reason: Optional[str] = None
    approved_task_id: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class TaskSuggestionListResponse(BaseModel):
    """Wrapper paginação-ready para ``GET /task-suggestions``."""

    suggestions: list[TaskSuggestionResponse]
    total: int
