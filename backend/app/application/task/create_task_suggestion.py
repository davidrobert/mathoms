"""Use case: cria TaskSuggestion pending (grava proposta do E5.N ou regra)."""

from __future__ import annotations

from backend.app.application.task._protocols import (
    TaskSuggestionRepositoryProtocol,
)
from backend.app.models.task import TaskSuggestion
from backend.app.schemas.dto.task import (
    TaskSuggestionCreateCommand,
    TaskSuggestionResponse,
    task_suggestion_to_response,
)


async def create_task_suggestion(
    cmd: TaskSuggestionCreateCommand,
    *,
    workspace_id: str,
    repo: TaskSuggestionRepositoryProtocol,
) -> TaskSuggestionResponse:
    sugg = TaskSuggestion(
        workspace_id=workspace_id,
        proposed_payload=cmd.proposed_payload.model_dump(),
        source=cmd.source,
        source_run_id=cmd.source_run_id,
        status="pending",
    )
    added = await repo.add(sugg)
    return task_suggestion_to_response(added)
