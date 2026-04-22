"""Use case: lista notificações com filtros + contadores de badge."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.notification import Notification
from backend.app.schemas.notifications import (
    NotificationListResponse,
    NotificationResponse,
)


async def list_notifications(
    workspace_id: str,
    *,
    db: AsyncSession,
    severity: Optional[str] = None,
    is_read: Optional[bool] = None,
    limit: int = 50,
) -> NotificationListResponse:
    items = await _fetch_items(
        workspace_id, db=db, severity=severity, is_read=is_read, limit=limit
    )
    unread = await _count(workspace_id, db=db, is_read=False)
    total = await _count(workspace_id, db=db)
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=unread,
    )


async def _fetch_items(
    workspace_id: str,
    *,
    db: AsyncSession,
    severity: Optional[str],
    is_read: Optional[bool],
    limit: int,
) -> list[Notification]:
    query = select(Notification).where(Notification.workspace_id == workspace_id)
    if severity:
        query = query.where(Notification.severity == severity)
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def _count(
    workspace_id: str,
    *,
    db: AsyncSession,
    is_read: Optional[bool] = None,
) -> int:
    query = select(func.count()).select_from(Notification).where(
        Notification.workspace_id == workspace_id
    )
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    result = await db.execute(query)
    return int(result.scalar() or 0)
