"""Use case: retorna uma Task ou levanta ``NotFoundError``."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.task._protocols import TaskRepositoryProtocol
from backend.app.schemas.dto.task import TaskResponse, task_to_response


async def get_task(
    workspace_id: str,
    task_id: str,
    *,
    repo: TaskRepositoryProtocol,
) -> TaskResponse:
    task = await repo.get_by_id(workspace_id, task_id)
    if task is None:
        raise NotFoundError(
            "Tarefa não encontrada",
            code="task_not_found",
        )
    return task_to_response(task)
