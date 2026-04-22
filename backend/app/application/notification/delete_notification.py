"""Use case: remove notificação do workspace (404 se não existir)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base import NotFoundError
from backend.app.models.notification import Notification


async def delete_notification(workspace_id: str, notification_id: str, *, db: AsyncSession) -> None:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.workspace_id == workspace_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise NotFoundError("Notificação não encontrada")
    await db.delete(notif)
    await db.commit()
