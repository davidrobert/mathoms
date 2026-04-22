"""Use case: update parcial da Task (status passa por ``transition_task_status``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.task._protocols import TaskRepositoryProtocol
from backend.app.application.task.transition_task_status import (
    transition_task_status,
)
from backend.app.events import dispatch_sync
from backend.app.events.domain import TaskUpdatedEvent
from backend.app.models.task import VALID_CATEGORIES
from backend.app.schemas.dto.task import (
    TaskResponse,
    TaskUpdateCommand,
    task_to_response,
)

if TYPE_CHECKING:  # pragma: no cover - só para type hints
    from sqlalchemy.ext.asyncio import AsyncSession


async def update_task(
    cmd: TaskUpdateCommand,
    *,
    workspace_id: str,
    task_id: str,
    repo: TaskRepositoryProtocol,
    db: "AsyncSession | None" = None,
    actor_user_id: str | None = None,
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

    if db is not None:
        await dispatch_sync(
            TaskUpdatedEvent(
                aggregate_id=saved.id,
                aggregate_type="task",
                workspace_id=workspace_id,
                task_id=saved.id,
                task_number=saved.number,
                task_title=saved.title,
                deadline_kind=saved.deadline_kind,
                deadline_date=saved.deadline_date,
                assigned_to=saved.assigned_to,
                actor_user_id=actor_user_id,
                changed_fields=tuple(data.keys()),
            ),
            {"db": db},
        )

    return task_to_response(saved)
