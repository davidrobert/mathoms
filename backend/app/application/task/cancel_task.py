"""Use case: soft-delete via transição para ``cancelled``."""

from __future__ import annotations

from backend.app.application.task._protocols import TaskRepositoryProtocol
from backend.app.application.task.transition_task_status import (
    transition_task_status,
)


async def cancel_task(
    workspace_id: str,
    task_id: str,
    *,
    repo: TaskRepositoryProtocol,
) -> None:
    """Cancela task (soft-delete preservando histórico — mesma semântica
    do endpoint ``DELETE /tasks/{id}``). Remoção física fica fora do MVP.
    """
    await transition_task_status(
        workspace_id,
        task_id,
        new_status="cancelled",
        repo=repo,
        reason="Cancelada via DELETE",
    )
