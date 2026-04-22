"""Use case: merge — anexa TaskSuggestion a Task existente (sem criar nova)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.task._protocols import (
    TaskRepositoryProtocol,
    TaskSuggestionRepositoryProtocol,
)
from backend.app.schemas.dto.task import (
    TaskSuggestionResponse,
    task_suggestion_to_response,
)


async def merge_suggestion_into_task(
    workspace_id: str,
    suggestion_id: str,
    target_task_id: str,
    *,
    suggestion_repo: TaskSuggestionRepositoryProtocol,
    task_repo: TaskRepositoryProtocol,
    reviewed_by: Optional[str] = None,
) -> TaskSuggestionResponse:
    """Útil quando E5.N sugere algo que já existe como Task — anexa a
    sugestão à task alvo (status=merged) em vez de duplicar.
    """
    sugg = await suggestion_repo.get_by_id(workspace_id, suggestion_id)
    if sugg is None:
        raise NotFoundError(
            "Sugestão não encontrada", code="suggestion_not_found"
        )
    if sugg.status != "pending":
        raise ConflictError(
            f"Sugestão já foi processada (status={sugg.status})",
            code="suggestion_not_pending",
        )

    target = await task_repo.get_by_id(workspace_id, target_task_id)
    if target is None:
        raise NotFoundError(
            "Tarefa alvo não encontrada", code="task_not_found"
        )

    sugg.status = "merged"
    sugg.approved_task_id = target.id
    sugg.reviewed_by = reviewed_by
    sugg.reviewed_at = datetime.now(timezone.utc)
    saved = await suggestion_repo.save(sugg)
    return task_suggestion_to_response(saved)
