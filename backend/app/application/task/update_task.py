"""Use case: update parcial da Task (status passa por ``transition_task_status``)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.task._protocols import TaskRepositoryProtocol
from backend.app.application.task.transition_task_status import (
    transition_task_status,
)
from backend.app.models.task import VALID_CATEGORIES
from backend.app.schemas.dto.task import (
    TaskResponse,
    TaskUpdateCommand,
    task_to_response,
)


async def update_task(
    cmd: TaskUpdateCommand,
    *,
    workspace_id: str,
    task_id: str,
    repo: TaskRepositoryProtocol,
) -> TaskResponse:
    """Mudança de status delega ao ``transition_task_status`` (mesma
    validação + timestamps). Outros campos são set direto na entidade.
    """
    if cmd.category is not None and cmd.category not in VALID_CATEGORIES:
        raise ValidationError(
            f"Categoria inválida: '{cmd.category}'. "
            f"Aceitas: {sorted(VALID_CATEGORIES)}",
            code="invalid_category",
        )

    task = await repo.get_by_id(workspace_id, task_id)
    if task is None:
        raise NotFoundError("Tarefa não encontrada", code="task_not_found")

    if cmd.status is not None and cmd.status != task.status:
        await transition_task_status(
            workspace_id,
            task_id,
            new_status=cmd.status,
            repo=repo,
            reason=cmd.status_reason,
        )
        task = await repo.get_by_id(workspace_id, task_id)
        assert task is not None  # acabou de existir na transição

    data = cmd.model_dump(exclude_unset=True, exclude={"status", "status_reason"})
    for key, value in data.items():
        setattr(task, key, value)
    saved = await repo.save(task)
    return task_to_response(saved)
