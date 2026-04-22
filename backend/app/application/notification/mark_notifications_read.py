"""Use case: marca um batch de notificações como lidas no workspace."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.notification import Notification
from backend.app.schemas.notifications import (
    NotificationMarkReadRequest,
    NotificationsMarkedReadResponse,
)


async def mark_notifications_read(
    workspace_id: str,
    body: NotificationMarkReadRequest,
    *,
    db: AsyncSession,
) -> NotificationsMarkedReadResponse:
    result = await db.execute(
        select(Notification).where(
            Notification.workspace_id == workspace_id,
            Notification.id.in_(body.notification_ids),
        )
    )
    updated = 0
    for notif in result.scalars().all():
        if not notif.is_read:
            notif.is_read = True
            updated += 1
    await db.commit()
    return NotificationsMarkedReadResponse(updated=updated)
