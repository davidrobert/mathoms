"""Use case: rejeição de TaskSuggestion pending."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.task._protocols import (
    TaskSuggestionRepositoryProtocol,
)
from backend.app.schemas.dto.task import (
    TaskSuggestionResponse,
    task_suggestion_to_response,
)


async def reject_task_suggestion(
    workspace_id: str,
    suggestion_id: str,
    *,
    repo: TaskSuggestionRepositoryProtocol,
    reviewed_by: Optional[str] = None,
    reason: Optional[str] = None,
) -> TaskSuggestionResponse:
    sugg = await repo.get_by_id(workspace_id, suggestion_id)
    if sugg is None:
        raise NotFoundError(
            "Sugestão não encontrada", code="suggestion_not_found"
        )
    if sugg.status != "pending":
        raise ConflictError(
            f"Sugestão já foi processada (status={sugg.status})",
            code="suggestion_not_pending",
        )

    sugg.status = "rejected"
    sugg.rejection_reason = reason
    sugg.reviewed_by = reviewed_by
    sugg.reviewed_at = datetime.now(timezone.utc)
    saved = await repo.save(sugg)
    return task_suggestion_to_response(saved)
