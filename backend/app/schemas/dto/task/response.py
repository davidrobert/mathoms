"""Response DTOs do agregado ``Task``.

``TaskBase`` define os campos comuns entre create/update/response.
``TaskResponse`` estende com metadados de persistência (id, number,
status, timestamps).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.dto.task.types import (
    CreatedFrom,
    DeadlineKind,
    Priority,
    TaskStatus,
)


class TaskBase(BaseModel):
    """Campos comuns entre create/update/response."""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=64)
    priority: Priority
    deadline_kind: DeadlineKind = "UNSCHEDULED"
    deadline_date: Optional[date] = None
    deadline_label: Optional[str] = Field(None, max_length=128)
    ref: Optional[str] = Field(None, max_length=255)
    parent_task_id: Optional[str] = None
    related_transaction_id: Optional[str] = None
    related_goal_id: Optional[str] = None
    assigned_to: Optional[str] = None
    # ADR-162 (Onda 8 #3) — Tasks geradas via DecisionCard "Gerar tarefas".
    derived_from_decision_id: Optional[str] = None


class TaskResponse(TaskBase):
    """Task persistida com metadata de estado e autoria."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    number: int
    status: TaskStatus
    status_reason: Optional[str] = None
    created_from: CreatedFrom
    source_suggestion_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Wrapper paginação-ready para ``GET /tasks``."""

    tasks: list[TaskResponse]
    total: int


class ScanDeadlinesResponse(BaseModel):
    """Resposta de ``POST /tasks/scan-deadlines`` — estatísticas do scan."""

    created: int
    skipped_existing: int
    evaluated: int
