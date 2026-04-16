"""Testes do `task_notification_service` (ADR-074 §F8.3)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from backend.app.models.notification import Notification
from backend.app.services.task_notification_service import (
    scan_and_create_notifications,
)
from backend.tests import factories


@pytest.mark.asyncio
async def test_scan_creates_notification_for_urgent_task(db):
    ws = await factories.make_workspace(db)
    today = date.today()
    await factories.make_task(
        db,
        workspace=ws,
        status="pending",
        deadline_kind="HARD_DATE",
        deadline_date=today + timedelta(days=2),
        title="Urgente",
    )
    await db.commit()

    stats = await scan_and_create_notifications(ws.id, db=db, today=today)
    await db.commit()

    assert stats["created"] == 1
    assert stats["skipped_existing"] == 0
    notifs = list(
        (await db.execute(select(Notification).where(Notification.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    assert len(notifs) == 1
    assert notifs[0].severity == "warning"
    assert "Urgente" in notifs[0].message
    assert notifs[0].source == "task_deadline"


@pytest.mark.asyncio
async def test_scan_classifies_overdue_as_critical(db):
    ws = await factories.make_workspace(db)
    today = date.today()
    await factories.make_task(
        db,
        workspace=ws,
        status="pending",
        deadline_kind="HARD_DATE",
        deadline_date=today - timedelta(days=5),
    )
    await db.commit()

    await scan_and_create_notifications(ws.id, db=db, today=today)
    await db.commit()

    notifs = list(
        (await db.execute(select(Notification).where(Notification.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    assert len(notifs) == 1
    assert notifs[0].severity == "critical"
    assert "venceu há" in notifs[0].message


@pytest.mark.asyncio
async def test_scan_classifies_soon_as_info(db):
    ws = await factories.make_workspace(db)
    today = date.today()
    await factories.make_task(
        db,
        workspace=ws,
        status="pending",
        deadline_kind="HARD_DATE",
        deadline_date=today + timedelta(days=6),
    )
    await db.commit()

    await scan_and_create_notifications(ws.id, db=db, today=today)
    await db.commit()

    notifs = list(
        (await db.execute(select(Notification).where(Notification.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    assert len(notifs) == 1
    assert notifs[0].severity == "info"


@pytest.mark.asyncio
async def test_scan_ignores_tasks_beyond_7_days(db):
    ws = await factories.make_workspace(db)
    today = date.today()
    await factories.make_task(
        db,
        workspace=ws,
        status="pending",
        deadline_kind="HARD_DATE",
        deadline_date=today + timedelta(days=30),
    )
    await db.commit()

    stats = await scan_and_create_notifications(ws.id, db=db, today=today)
    assert stats["created"] == 0


@pytest.mark.asyncio
async def test_scan_ignores_done_and_cancelled_tasks(db):
    ws = await factories.make_workspace(db)
    today = date.today()
    await factories.make_task(
        db,
        workspace=ws,
        status="done",
        deadline_kind="HARD_DATE",
        deadline_date=today - timedelta(days=2),
    )
    await factories.make_task(
        db,
        workspace=ws,
        status="cancelled",
        deadline_kind="HARD_DATE",
        deadline_date=today - timedelta(days=2),
    )
    await db.commit()

    stats = await scan_and_create_notifications(ws.id, db=db, today=today)
    assert stats["created"] == 0


@pytest.mark.asyncio
async def test_scan_ignores_non_hard_date_kinds(db):
    ws = await factories.make_workspace(db)
    today = date.today()
    # MONTH, QUARTER, CONDITIONAL, UNSCHEDULED — não gera notif mesmo com data
    for kind in ("MONTH", "QUARTER", "CONDITIONAL", "UNSCHEDULED"):
        await factories.make_task(
            db,
            workspace=ws,
            status="pending",
            deadline_kind=kind,
            deadline_date=today + timedelta(days=2),
            deadline_label=f"label-{kind}",
        )
    await db.commit()

    stats = await scan_and_create_notifications(ws.id, db=db, today=today)
    assert stats["created"] == 0


@pytest.mark.asyncio
async def test_scan_is_idempotent(db):
    ws = await factories.make_workspace(db)
    today = date.today()
    await factories.make_task(
        db,
        workspace=ws,
        status="pending",
        deadline_kind="HARD_DATE",
        deadline_date=today + timedelta(days=1),
    )
    await db.commit()

    stats1 = await scan_and_create_notifications(ws.id, db=db, today=today)
    await db.commit()
    stats2 = await scan_and_create_notifications(ws.id, db=db, today=today)

    assert stats1["created"] == 1
    assert stats2["created"] == 0
    assert stats2["skipped_existing"] == 1


@pytest.mark.asyncio
async def test_scan_isolated_between_workspaces(db):
    ws_a = await factories.make_workspace(db)
    ws_b = await factories.make_workspace(db)
    today = date.today()
    await factories.make_task(
        db,
        workspace=ws_a,
        status="pending",
        deadline_kind="HARD_DATE",
        deadline_date=today + timedelta(days=1),
        title="A-urgente",
    )
    await factories.make_task(
        db,
        workspace=ws_b,
        status="pending",
        deadline_kind="HARD_DATE",
        deadline_date=today + timedelta(days=1),
        title="B-urgente",
    )
    await db.commit()

    await scan_and_create_notifications(ws_a.id, db=db, today=today)
    await db.commit()

    notifs_a = list(
        (await db.execute(select(Notification).where(Notification.workspace_id == ws_a.id)))
        .scalars()
        .all()
    )
    notifs_b = list(
        (await db.execute(select(Notification).where(Notification.workspace_id == ws_b.id)))
        .scalars()
        .all()
    )
    assert len(notifs_a) == 1
    assert len(notifs_b) == 0
    assert "A-urgente" in notifs_a[0].message
