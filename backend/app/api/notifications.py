"""Notifications API — CRUD for workspace notifications (tenant-scoped, ADR-072)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.notification import Notification
from backend.app.models.workspace import Workspace
from backend.app.schemas.notifications import (
    NotificationListResponse,
    NotificationMarkReadRequest,
    NotificationResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/notifications",
    tags=["notifications"],
)


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    severity: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(Notification.workspace_id == workspace.id)

    if severity:
        query = query.where(Notification.severity == severity)
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)

    query = query.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    unread_result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.workspace_id == workspace.id, Notification.is_read == False)  # noqa: E712
    )
    unread_count = unread_result.scalar() or 0

    total_result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.workspace_id == workspace.id)
    )
    total = total_result.scalar() or 0

    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=unread_count,
    )


@router.patch("/read", status_code=status.HTTP_200_OK)
async def mark_read(
    body: NotificationMarkReadRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.workspace_id == workspace.id,
            Notification.id.in_(body.notification_ids),
        )
    )
    notifications = result.scalars().all()
    updated = 0
    for notif in notifications:
        if not notif.is_read:
            notif.is_read = True
            updated += 1
    await db.commit()
    return {"updated": updated}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.workspace_id == workspace.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    await db.delete(notif)
    await db.commit()
