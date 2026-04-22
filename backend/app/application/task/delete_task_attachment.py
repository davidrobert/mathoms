"""Use case: remove row de TaskAttachment (arquivo em disco fica no composite)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.task._protocols import (
    TaskAttachmentRepositoryProtocol,
)
from backend.app.models.task import TaskAttachment


async def delete_task_attachment(
    workspace_id: str,
    task_id: str,
    attachment_id: str,
    *,
    repo: TaskAttachmentRepositoryProtocol,
) -> TaskAttachment:
    """Remove apenas a row ``task_attachments``. Remoção do arquivo físico
    continua no router/service (side-effect de storage — composite).
    Retorna a entidade para o caller poder resolver o path ao deletar o
    blob no filesystem.
    """
    attachment = await repo.get_by_id(workspace_id, attachment_id)
    if attachment is None:
        raise NotFoundError("Anexo não encontrado", code="attachment_not_found")
    if attachment.task_id != task_id:
        raise NotFoundError(
            "Anexo não pertence à task informada",
            code="attachment_task_mismatch",
        )
    await repo.delete(attachment)
    return attachment
