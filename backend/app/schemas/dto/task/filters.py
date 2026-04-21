"""Filtros/query params do ``GET /tasks`` (ADR-074)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel

from backend.app.schemas.dto.task.types import Priority, TaskStatus


class TaskFilters(BaseModel):
    """Query params aceitos pelo ``GET /tasks``. Todos opcionais.

    Sem ``status`` explícito, default exclui ``done`` / ``cancelled``
    a menos que ``include_*`` sejam ``true``.
    """

    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    category: Optional[str] = None
    deadline_before: Optional[date] = None
    deadline_after: Optional[date] = None
    assigned_to: Optional[str] = None
    related_goal_id: Optional[str] = None
    include_done: bool = False
    include_cancelled: bool = False
