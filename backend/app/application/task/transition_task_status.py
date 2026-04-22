"""Use case: transição validada de status + timestamps de done/cancelled."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.application.task._protocols import TaskRepositoryProtocol
from backend.app.application.task._rules import ALLOWED_TRANSITIONS
from backend.app.models.task import VALID_STATUSES, Task
from backend.app.schemas.dto.task import TaskResponse, task_to_response


async def transition_task_status(
    workspace_id: str,
    task_id: str,
    *,
    new_status: str,
    repo: TaskRepositoryProtocol,
    reason: Optional[str] = None,
) -> TaskResponse:
    """Enforça grafo ``ALLOWED_TRANSITIONS`` + dependency check de parent
    (``done`` só aceita se parent está em ``{done, cancelled}``).
    """
    if new_status not in VALID_STATUSES:
        raise ValidationError(
            f"Status inválido: {new_status}",
            code="invalid_status",
        )

    task = await _load_task(repo, workspace_id, task_id)
    if task.status == new_status:
        return task_to_response(task)

    _ensure_transition_allowed(task.status, new_status)
    if new_status == "done" and task.parent_task_id:
        await _ensure_parent_done(repo, workspace_id, task.parent_task_id)

    _apply_transition(task, new_status, reason)
    saved = await repo.save(task)
    return task_to_response(saved)


async def _load_task(repo: TaskRepositoryProtocol, workspace_id: str, task_id: str) -> Task:
    task = await repo.get_by_id(workspace_id, task_id)
    if task is None:
        raise NotFoundError("Tarefa não encontrada", code="task_not_found")
    return task


def _ensure_transition_allowed(current: str, new_status: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if new_status not in allowed:
        raise ConflictError(
            f"Transição não permitida: {current} → {new_status}. "
            f"Aceitas a partir de '{current}': {sorted(allowed)}",
            code="invalid_transition",
        )


async def _ensure_parent_done(
    repo: TaskRepositoryProtocol,
    workspace_id: str,
    parent_task_id: str,
) -> None:
    parent = await repo.get_by_id(workspace_id, parent_task_id)
    if parent is not None and parent.status not in ("done", "cancelled"):
        raise ConflictError(
            f"Parent task #{parent.number} ({parent.status}) não "
            f"está concluída. Conclua a dependência primeiro.",
            code="parent_not_done",
        )


def _apply_transition(task: Task, new_status: str, reason: Optional[str]) -> None:
    now = datetime.now(timezone.utc)
    task.status = new_status
    task.status_reason = reason
    if new_status == "done":
        task.completed_at = now
    if new_status == "cancelled":
        task.cancelled_at = now
    # Reabrir de done/cancelled → zera timestamps correspondentes
    if new_status in ("pending", "in_progress"):
        task.completed_at = None
        task.cancelled_at = None
