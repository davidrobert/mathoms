"""Notifications router fino — CRUD por workspace (A6e.4 · ADR-072 · ADR-101 R15/R16)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.notification import (
    delete_notification as _delete_notification,
    list_notifications as _list_notifications,
    mark_notifications_read as _mark_notifications_read,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace
from backend.app.schemas.notifications import (
    NotificationListResponse,
    NotificationMarkReadRequest,
    NotificationsMarkedReadResponse,
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
) -> NotificationListResponse:
    return await _list_notifications(
        workspace.id,
        db=db,
        severity=severity,
        is_read=is_read,
        limit=limit,
    )


@router.patch(
    "/read",
    response_model=NotificationsMarkedReadResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_read(
    body: NotificationMarkReadRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> NotificationsMarkedReadResponse:
    return await _mark_notifications_read(workspace.id, body, db=db)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _delete_notification(workspace.id, notification_id, db=db)
