"""Use case: cria uma Task nova (status inicial ``pending``)."""

from __future__ import annotations

from typing import Optional

from backend.app.application.base.errors import ValidationError
from backend.app.application.task._protocols import TaskRepositoryProtocol
from backend.app.models.task import VALID_CATEGORIES, Task
from backend.app.schemas.dto.task import (
    TaskCreateCommand,
    TaskResponse,
    task_to_response,
)


async def create_task(
    cmd: TaskCreateCommand,
    *,
    workspace_id: str,
    repo: TaskRepositoryProtocol,
    created_by: Optional[str] = None,
    created_from: str = "manual",
    source_suggestion_id: Optional[str] = None,
) -> TaskResponse:
    """``_number`` vem de ``repo.next_number`` se o cmd não especifica —
    repo é responsável por atomicidade (flush pré-commit detecta colisão
    de ``UNIQUE (workspace_id, number)``).
    """
    _validate_category(cmd.category)
    await _validate_parent(repo, workspace_id, cmd.parent_task_id)

    number = cmd.number or await repo.next_number(workspace_id)
    task = Task(
        workspace_id=workspace_id,
        number=number,
        title=cmd.title,
        description=cmd.description,
        category=cmd.category,
        priority=cmd.priority,
        deadline_kind=cmd.deadline_kind,
        deadline_date=cmd.deadline_date,
        deadline_label=cmd.deadline_label,
        ref=cmd.ref,
        parent_task_id=cmd.parent_task_id,
        related_transaction_id=cmd.related_transaction_id,
        related_goal_id=cmd.related_goal_id,
        assigned_to=cmd.assigned_to,
        created_by=created_by,
        created_from=created_from,
        source_suggestion_id=source_suggestion_id,
        status="pending",
    )
    added = await repo.add(task)
    return task_to_response(added)


def _validate_category(category: Optional[str]) -> None:
    if category is not None and category not in VALID_CATEGORIES:
        raise ValidationError(
            f"Categoria inválida: '{category}'. "
            f"Aceitas: {sorted(VALID_CATEGORIES)}",
            code="invalid_category",
        )


async def _validate_parent(
    repo: TaskRepositoryProtocol,
    workspace_id: str,
    parent_task_id: Optional[str],
) -> None:
    if not parent_task_id:
        return
    parent = await repo.get_by_id(workspace_id, parent_task_id)
    if parent is None:
        raise ValidationError(
            "parent_task_id inválido (não pertence ao workspace)",
            code="invalid_parent",
        )
