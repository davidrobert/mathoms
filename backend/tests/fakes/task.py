"""Fakes in-memory dos repositórios de ``Task`` + sub-agregados.

Implementam os Protocols declarados em
``backend.app.application.task._protocols`` via duck typing.

Os 3 repositórios reais vivem em
``backend.app.repositories.task_repository``,
``task_suggestion_repository`` e ``task_attachment_repository`` — estes
fakes espelham-nos quanto basta para exercitar use cases sem DB.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.models.task import Task, TaskAttachment, TaskSuggestion
from backend.app.schemas.dto.task import TaskFilters


def _matches_filter(task: Task, f: TaskFilters) -> bool:
    """Reproduz a lógica de ``TaskRepository.list`` sem o SQL."""
    if f.status is not None:
        if task.status != f.status:
            return False
    else:
        if not f.include_done and task.status == "done":
            return False
        if not f.include_cancelled and task.status == "cancelled":
            return False
    if f.priority is not None and task.priority != f.priority:
        return False
    if f.category is not None and task.category != f.category:
        return False
    if f.deadline_before is not None:
        if task.deadline_date is None or task.deadline_date > f.deadline_before:
            return False
    if f.deadline_after is not None:
        if task.deadline_date is None or task.deadline_date < f.deadline_after:
            return False
    if f.assigned_to is not None and task.assigned_to != f.assigned_to:
        return False
    if f.related_goal_id is not None and task.related_goal_id != f.related_goal_id:
        return False
    return True


_PRIORITY_RANK = {"S": 1, "R": 2, "O": 3}


def _sort_key(task: Task) -> tuple[int, int, str, int]:
    rank = _PRIORITY_RANK.get((task.priority or "").upper(), 99)
    deadline_missing = 0 if task.deadline_date is not None else 1
    deadline_iso = task.deadline_date.isoformat() if task.deadline_date else ""
    return (rank, deadline_missing, deadline_iso, task.number)


class FakeTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def _ensure_defaults(self, task: Task) -> None:
        if not task.id:
            task.id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        if task.created_at is None:
            task.created_at = now
        task.updated_at = now

    async def list(
        self, workspace_id: str, filters: TaskFilters
    ) -> list[Task]:
        tasks = [
            t for t in self._tasks.values()
            if t.workspace_id == workspace_id and _matches_filter(t, filters)
        ]
        tasks.sort(key=_sort_key)
        return tasks

    async def list_all(self, workspace_id: str) -> list[Task]:
        tasks = [
            t for t in self._tasks.values() if t.workspace_id == workspace_id
        ]
        tasks.sort(key=lambda t: t.number)
        return tasks

    async def get_by_id(
        self, workspace_id: str, task_id: str
    ) -> Optional[Task]:
        t = self._tasks.get(task_id)
        if t is None or t.workspace_id != workspace_id:
            return None
        return t

    async def next_number(self, workspace_id: str) -> int:
        numbers = [
            t.number for t in self._tasks.values()
            if t.workspace_id == workspace_id and t.number is not None
        ]
        return (max(numbers) + 1) if numbers else 1

    async def add(self, task: Task, *, flush: bool = True) -> Task:
        self._ensure_defaults(task)
        # Viola UNIQUE(workspace_id, number) ≅ comportamento real do repo.
        collision = any(
            t.workspace_id == task.workspace_id and t.number == task.number
            for t in self._tasks.values()
        )
        if collision:
            raise RuntimeError(
                f"duplicate number {task.number} for workspace {task.workspace_id}"
            )
        self._tasks[task.id] = task
        return task

    async def save(self, task: Task) -> Task:
        self._ensure_defaults(task)
        self._tasks[task.id] = task
        return task


class FakeTaskSuggestionRepository:
    def __init__(self) -> None:
        self._suggestions: dict[str, TaskSuggestion] = {}

    def _ensure_defaults(self, sugg: TaskSuggestion) -> None:
        if not sugg.id:
            sugg.id = str(uuid.uuid4())
        if sugg.created_at is None:
            sugg.created_at = datetime.now(timezone.utc)

    async def list_by_status(
        self, workspace_id: str, status: Optional[str] = "pending"
    ) -> list[TaskSuggestion]:
        items = [
            s for s in self._suggestions.values()
            if s.workspace_id == workspace_id
            and (status is None or s.status == status)
        ]
        items.sort(key=lambda s: s.created_at, reverse=True)
        return items

    async def get_by_id(
        self, workspace_id: str, suggestion_id: str
    ) -> Optional[TaskSuggestion]:
        s = self._suggestions.get(suggestion_id)
        if s is None or s.workspace_id != workspace_id:
            return None
        return s

    async def add(
        self, suggestion: TaskSuggestion, *, flush: bool = True
    ) -> TaskSuggestion:
        self._ensure_defaults(suggestion)
        self._suggestions[suggestion.id] = suggestion
        return suggestion

    async def save(self, suggestion: TaskSuggestion) -> TaskSuggestion:
        self._ensure_defaults(suggestion)
        self._suggestions[suggestion.id] = suggestion
        return suggestion


class FakeTaskAttachmentRepository:
    def __init__(self) -> None:
        self._attachments: dict[str, TaskAttachment] = {}

    def _ensure_defaults(self, att: TaskAttachment) -> None:
        if not att.id:
            att.id = str(uuid.uuid4())
        if att.created_at is None:
            att.created_at = datetime.now(timezone.utc)

    async def list_by_task(
        self, workspace_id: str, task_id: str
    ) -> list[TaskAttachment]:
        items = [
            a for a in self._attachments.values()
            if a.workspace_id == workspace_id and a.task_id == task_id
        ]
        items.sort(key=lambda a: a.created_at, reverse=True)
        return items

    async def get_by_id(
        self, workspace_id: str, attachment_id: str
    ) -> Optional[TaskAttachment]:
        a = self._attachments.get(attachment_id)
        if a is None or a.workspace_id != workspace_id:
            return None
        return a

    async def add(
        self, attachment: TaskAttachment, *, flush: bool = True
    ) -> TaskAttachment:
        self._ensure_defaults(attachment)
        self._attachments[attachment.id] = attachment
        return attachment

    async def delete(self, attachment: TaskAttachment) -> None:
        self._attachments.pop(attachment.id, None)


__all__ = [
    "FakeTaskAttachmentRepository",
    "FakeTaskRepository",
    "FakeTaskSuggestionRepository",
]
