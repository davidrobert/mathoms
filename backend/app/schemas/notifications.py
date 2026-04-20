"""Pydantic schemas for Notification endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    severity: str
    title: str
    message: str
    source: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    unread_count: int


class NotificationMarkReadRequest(BaseModel):
    notification_ids: list[str]


class NotificationsMarkedReadResponse(BaseModel):
    """Resposta de ``PATCH /notifications/read`` — contador de atualizadas."""

    updated: int
