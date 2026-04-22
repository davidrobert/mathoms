"""Use case: lista anexos de uma Task (com tenancy check via task_repo)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.task._protocols import (
    TaskAttachmentRepositoryProtocol,
    TaskRepositoryProtocol,
)
from backend.app.schemas.dto.task import (
    TaskAttachmentListResponse,
    task_attachment_to_response,
)


async def list_task_attachments(
    workspace_id: str,
    task_id: str,
    *,
    task_repo: TaskRepositoryProtocol,
    attachment_repo: TaskAttachmentRepositoryProtocol,
) -> TaskAttachmentListResponse:
    task = await task_repo.get_by_id(workspace_id, task_id)
    if task is None:
        raise NotFoundError("Tarefa não encontrada", code="task_not_found")

    items = await attachment_repo.list_by_task(workspace_id, task_id)
    return TaskAttachmentListResponse(
        attachments=[task_attachment_to_response(a) for a in items],
        total=len(items),
    )
