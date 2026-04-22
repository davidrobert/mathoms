"""Use cases de notificação (A6e.4 · ADR-072)."""

from __future__ import annotations

import pytest

from backend.app.application.base import NotFoundError
from backend.app.application.notification import (
    delete_notification,
    list_notifications,
    mark_notifications_read,
)
from backend.app.schemas.notifications import NotificationMarkReadRequest
from backend.tests import factories


@pytest.mark.asyncio
async def test_list_includes_total_and_unread_count(db):
    ws = await factories.make_workspace(db)
    await factories.make_notification(db, workspace=ws, is_read=False)
    await factories.make_notification(db, workspace=ws, is_read=True)
    await factories.make_notification(db, workspace=ws, is_read=False)

    resp = await list_notifications(ws.id, db=db)
    assert resp.total == 3
    assert resp.unread_count == 2


@pytest.mark.asyncio
async def test_list_filter_by_severity(db):
    ws = await factories.make_workspace(db)
    await factories.make_notification(db, workspace=ws, severity="info")
    await factories.make_notification(db, workspace=ws, severity="error")

    resp = await list_notifications(ws.id, db=db, severity="error")
    assert len(resp.notifications) == 1
    assert resp.notifications[0].severity == "error"


@pytest.mark.asyncio
async def test_mark_read_updates_only_unread(db):
    ws = await factories.make_workspace(db)
    n1 = await factories.make_notification(db, workspace=ws, is_read=False)
    n2 = await factories.make_notification(db, workspace=ws, is_read=True)

    resp = await mark_notifications_read(
        ws.id,
        NotificationMarkReadRequest(notification_ids=[n1.id, n2.id]),
        db=db,
    )
    assert resp.updated == 1


@pytest.mark.asyncio
async def test_delete_existing(db):
    ws = await factories.make_workspace(db)
    n = await factories.make_notification(db, workspace=ws)
    await delete_notification(ws.id, n.id, db=db)

    resp = await list_notifications(ws.id, db=db)
    assert resp.total == 0


@pytest.mark.asyncio
async def test_delete_missing_raises_not_found(db):
    ws = await factories.make_workspace(db)
    with pytest.raises(NotFoundError):
        await delete_notification(ws.id, "none", db=db)
