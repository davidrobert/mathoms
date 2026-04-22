"""Use case: lista TaskSuggestions do workspace por status (default ``pending``)."""

from __future__ import annotations

from typing import Optional

from backend.app.application.task._protocols import (
    TaskSuggestionRepositoryProtocol,
)
from backend.app.schemas.dto.task import (
    TaskSuggestionListResponse,
    task_suggestion_to_response,
)


async def list_task_suggestions(
    workspace_id: str,
    *,
    repo: TaskSuggestionRepositoryProtocol,
    status: Optional[str] = "pending",
) -> TaskSuggestionListResponse:
    suggestions = await repo.list_by_status(workspace_id, status=status)
    return TaskSuggestionListResponse(
        suggestions=[task_suggestion_to_response(s) for s in suggestions],
        total=len(suggestions),
    )
