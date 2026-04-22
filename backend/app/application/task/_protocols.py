"""Protocols consumidos pelos use cases do agregado ``Task``.

3 Protocols, um por sub-agregado (``Task``, ``TaskSuggestion``,
``TaskAttachment``) — espelham os repositórios SQLAlchemy
(``backend.app.repositories.task_repository``,
``task_suggestion_repository``, ``task_attachment_repository``) via
duck typing. Fakes em ``backend.tests.fakes.task`` implementam os 3.
"""

from __future__ import annotations

from typing import Optional, Protocol

from backend.app.models.task import Task, TaskAttachment, TaskSuggestion
from backend.app.schemas.dto.task import TaskFilters


class TaskRepositoryProtocol(Protocol):
    async def list(
        self, workspace_id: str, filters: TaskFilters
    ) -> list[Task]: ...

    async def list_all(self, workspace_id: str) -> list[Task]: ...

    async def get_by_id(
        self, workspace_id: str, task_id: str
    ) -> Optional[Task]: ...

    async def next_number(self, workspace_id: str) -> int: ...

    async def add(self, task: Task, *, flush: bool = True) -> Task: ...

    async def save(self, task: Task) -> Task: ...


class TaskSuggestionRepositoryProtocol(Protocol):
    async def list_by_status(
        self, workspace_id: str, status: Optional[str] = "pending"
    ) -> list[TaskSuggestion]: ...

    async def get_by_id(
        self, workspace_id: str, suggestion_id: str
    ) -> Optional[TaskSuggestion]: ...

    async def add(
        self, suggestion: TaskSuggestion, *, flush: bool = True
    ) -> TaskSuggestion: ...

    async def save(self, suggestion: TaskSuggestion) -> TaskSuggestion: ...


class TaskAttachmentRepositoryProtocol(Protocol):
    async def list_by_task(
        self, workspace_id: str, task_id: str
    ) -> list[TaskAttachment]: ...

    async def get_by_id(
        self, workspace_id: str, attachment_id: str
    ) -> Optional[TaskAttachment]: ...

    async def delete(self, attachment: TaskAttachment) -> None: ...
