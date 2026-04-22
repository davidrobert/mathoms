"""TaskAttachmentRepository — CRUD async para ``TaskAttachment``.

``TaskAttachment`` é aggregate próprio: sua persistência no DB é
independente do arquivo físico (``storage_path`` é string). A camada
de storage (``StorageService``) fica no service que compõe os dois —
**este repo só fala DB**.

R13 (ADR-101): toda query inclui ``workspace_id`` (+ opcionalmente
``task_id``) no predicado. R14: não commita.

Uso::

    repo = TaskAttachmentRepository(session)
    items = await repo.list_by_task(ws_id, task_id)
    att = await repo.get_by_id(ws_id, attachment_id)
    await repo.add(new_attachment)
    await repo.delete(att)
    await session.commit()
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.task import TaskAttachment


class TaskAttachmentRepository:
    """Single Responsibility: persistência de ``TaskAttachment`` (só DB)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def list_by_task(self, workspace_id: str, task_id: str) -> list[TaskAttachment]:
        """Lista anexos de uma task, mais recentes primeiro."""
        result = await self._session.execute(
            select(TaskAttachment)
            .where(
                TaskAttachment.workspace_id == workspace_id,
                TaskAttachment.task_id == task_id,
            )
            .order_by(TaskAttachment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, workspace_id: str, attachment_id: str) -> Optional[TaskAttachment]:
        """Retorna anexo por id dentro do workspace, ou ``None``."""
        result = await self._session.execute(
            select(TaskAttachment).where(
                TaskAttachment.workspace_id == workspace_id,
                TaskAttachment.id == attachment_id,
            )
        )
        return result.scalar_one_or_none()

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def add(self, attachment: TaskAttachment, *, flush: bool = True) -> TaskAttachment:
        """Registra ``attachment`` na sessão. Caller commita."""
        self._session.add(attachment)
        if flush:
            await self._session.flush()
        return attachment

    async def delete(self, attachment: TaskAttachment) -> None:
        """Remove a row. Arquivo em disco é responsabilidade do caller."""
        await self._session.delete(attachment)
