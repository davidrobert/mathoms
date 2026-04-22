"""Use case: aprovação de TaskSuggestion — cria Task + marca approved."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.task._protocols import (
    TaskRepositoryProtocol,
    TaskSuggestionRepositoryProtocol,
)
from backend.app.application.task.create_task import create_task
from backend.app.schemas.dto.task import (
    TaskCreateCommand,
    TaskResponse,
    TaskSuggestionApproveCommand,
    TaskSuggestionResponse,
    task_suggestion_to_response,
)


async def approve_task_suggestion(
    workspace_id: str,
    suggestion_id: str,
    *,
    suggestion_repo: TaskSuggestionRepositoryProtocol,
    task_repo: TaskRepositoryProtocol,
    reviewed_by: Optional[str] = None,
    body: Optional[TaskSuggestionApproveCommand] = None,
) -> tuple[TaskSuggestionResponse, TaskResponse]:
    """``body.edited_payload`` (se presente) sobrescreve ``proposed_payload``
    — permite o usuário ajustar antes de aceitar.
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

    payload = (
        body.edited_payload.model_dump()
        if body and body.edited_payload
        else sugg.proposed_payload
    )
    task_cmd = TaskCreateCommand(**payload)
    task_resp = await create_task(
        task_cmd,
        workspace_id=workspace_id,
        repo=task_repo,
        created_by=reviewed_by,
        created_from="llm_suggestion",
        source_suggestion_id=sugg.id,
    )

    sugg.status = "approved"
    sugg.reviewed_by = reviewed_by
    sugg.reviewed_at = datetime.now(timezone.utc)
    sugg.approved_task_id = task_resp.id
    saved = await suggestion_repo.save(sugg)
    return task_suggestion_to_response(saved), task_resp
