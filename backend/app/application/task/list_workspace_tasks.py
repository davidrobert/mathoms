"""Use case: lista tasks do workspace aplicando filtros."""

from __future__ import annotations

from backend.app.application.task._protocols import TaskRepositoryProtocol
from backend.app.schemas.dto.task import (
    TaskFilters,
    TaskListResponse,
    task_to_response,
)


async def list_workspace_tasks(
    workspace_id: str,
    filters: TaskFilters,
    *,
    repo: TaskRepositoryProtocol,
) -> TaskListResponse:
    """Ordenação S→R→O + deadline asc + number asc (responsabilidade do repo)."""
    tasks = await repo.list(workspace_id, filters)
    return TaskListResponse(
        tasks=[task_to_response(t) for t in tasks],
        total=len(tasks),
    )
