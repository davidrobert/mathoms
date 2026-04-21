"""Command DTOs (inputs de write) do agregado ``Task``.

- ``TaskCreateCommand``: input do ``POST /tasks`` — o ``number`` é
  auto-atribuído pelo service/repo (``max(number) + 1``), mas o caller
  pode forçar um valor específico (usado pelo importer de
  ``tarefas.md`` para preservar numeração histórica).
- ``TaskUpdateCommand``: ``PATCH /tasks/{id}`` — todos os campos
  opcionais (semântica ``exclude_unset``). Transição de status aqui
  passa pela validação do service (ver ``TaskStatusTransitionCommand``
  para audit trail dedicado).
- ``TaskStatusTransitionCommand``: ``POST /tasks/{id}/status`` —
  endpoint dedicado para transições com motivo explícito.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from backend.app.schemas.dto.task.response import TaskBase
from backend.app.schemas.dto.task.types import (
    DeadlineKind,
    Priority,
    TaskStatus,
)


class TaskCreateCommand(TaskBase):
    """Body do ``POST /tasks``."""

    number: Optional[int] = None


class TaskUpdateCommand(BaseModel):
    """``PATCH /tasks/{id}`` — todos os campos opcionais."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=64)
    priority: Optional[Priority] = None
    deadline_kind: Optional[DeadlineKind] = None
    deadline_date: Optional[date] = None
    deadline_label: Optional[str] = Field(None, max_length=128)
    ref: Optional[str] = Field(None, max_length=255)
    parent_task_id: Optional[str] = None
    related_transaction_id: Optional[str] = None
    related_goal_id: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[TaskStatus] = None
    status_reason: Optional[str] = None


class TaskStatusTransitionCommand(BaseModel):
    """``POST /tasks/{id}/status`` — transição com motivo explícito.

    Separado do PATCH para audit trail mais claro em Swagger/logs.
    """

    status: TaskStatus
    status_reason: Optional[str] = Field(None, max_length=1000)
