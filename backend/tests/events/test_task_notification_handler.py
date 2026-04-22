"""Integration — TaskCreated/Updated → Notification handler (A6e.events slice 3)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from backend.app.application.task import create_task, update_task
from backend.app.core.config import settings
from backend.app.models.notification import Notification
from backend.app.repositories.task_repository import TaskRepository
from backend.app.schemas.dto.task import TaskCreateCommand, TaskUpdateCommand
from backend.tests.factories import make_task, make_workspace


@pytest.fixture
def enable_event_driven(monkeypatch):
    monkeypatch.setattr(settings, "USE_EVENT_DRIVEN_TASK_NOTIFICATIONS", True)


@pytest.mark.asyncio
async def test_create_task_inside_horizon_creates_notification(db, enable_event_driven):
    ws = await make_workspace(db)
    await db.commit()

    repo = TaskRepository(db)
    today = date.today()
    deadline = today + timedelta(days=2)

    resp = await create_task(
        TaskCreateCommand(
            title="Revisar alocação",
            category="Invest",
            priority="S",
            deadline_kind="HARD_DATE",
            deadline_date=deadline,
        ),
        workspace_id=ws.id,
        repo=repo,
        db=db,
    )
    await db.commit()

    rows = (
        (await db.execute(select(Notification).where(Notification.workspace_id == ws.id)))
        .scalars()
        .all()
    )

    assert len(rows) == 1
    n = rows[0]
    assert n.severity == "warning"  # urgent bucket (<=3 dias)
    assert f"[#{resp.number}:urgent]" in n.title
    assert "Revisar alocação" in n.message
    assert n.source == "task_deadline"


@pytest.mark.asyncio
async def test_create_task_overdue_creates_critical_notification(db, enable_event_driven):
    ws = await make_workspace(db)
    await db.commit()

    repo = TaskRepository(db)
    past = date.today() - timedelta(days=5)

    await create_task(
        TaskCreateCommand(
            title="Atrasou",
            category="Invest",
            priority="S",
            deadline_kind="HARD_DATE",
            deadline_date=past,
        ),
        workspace_id=ws.id,
        repo=repo,
        db=db,
    )
    await db.commit()

    n = (
        await db.execute(select(Notification).where(Notification.workspace_id == ws.id))
    ).scalar_one()
    assert n.severity == "critical"
    assert ":overdue]" in n.title


@pytest.mark.asyncio
async def test_create_task_outside_horizon_does_not_notify(db, enable_event_driven):
    ws = await make_workspace(db)
    await db.commit()

    repo = TaskRepository(db)
    far = date.today() + timedelta(days=30)

    await create_task(
        TaskCreateCommand(
            title="Distante",
            category="Invest",
            priority="S",
            deadline_kind="HARD_DATE",
            deadline_date=far,
        ),
        workspace_id=ws.id,
        repo=repo,
        db=db,
    )
    await db.commit()

    rows = (
        (await db.execute(select(Notification).where(Notification.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    assert rows == []


@pytest.mark.asyncio
async def test_handler_noop_when_flag_disabled(db):
    # Flag default = False → handler não cria Notification
    ws = await make_workspace(db)
    await db.commit()

    repo = TaskRepository(db)
    deadline = date.today() + timedelta(days=2)

    await create_task(
        TaskCreateCommand(
            title="Sem flag",
            category="Invest",
            priority="S",
            deadline_kind="HARD_DATE",
            deadline_date=deadline,
        ),
        workspace_id=ws.id,
        repo=repo,
        db=db,
    )
    await db.commit()

    rows = (
        (await db.execute(select(Notification).where(Notification.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    assert rows == []


@pytest.mark.asyncio
async def test_update_task_to_urgent_deadline_creates_notification(db, enable_event_driven):
    ws = await make_workspace(db)
    task = await make_task(db, workspace=ws, title="Existente")
    await db.commit()

    repo = TaskRepository(db)
    urgent = date.today() + timedelta(days=1)

    await update_task(
        TaskUpdateCommand(
            deadline_kind="HARD_DATE",
            deadline_date=urgent,
        ),
        workspace_id=ws.id,
        task_id=task.id,
        repo=repo,
        db=db,
    )
    await db.commit()

    rows = (
        (await db.execute(select(Notification).where(Notification.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].severity == "warning"


@pytest.mark.asyncio
async def test_dedupe_by_title_prevents_duplicate(db, enable_event_driven):
    ws = await make_workspace(db)
    await db.commit()

    repo = TaskRepository(db)
    deadline = date.today() + timedelta(days=2)

    # Criar task → emite TaskCreatedEvent (cria notification)
    resp = await create_task(
        TaskCreateCommand(
            title="Dupe test",
            category="Invest",
            priority="S",
            deadline_kind="HARD_DATE",
            deadline_date=deadline,
        ),
        workspace_id=ws.id,
        repo=repo,
        db=db,
    )
    await db.commit()

    # Update task (mesmo bucket) — dedupe NÃO cria segunda notification
    await update_task(
        TaskUpdateCommand(title="Dupe test renomeada"),
        workspace_id=ws.id,
        task_id=resp.id,
        repo=repo,
        db=db,
    )
    await db.commit()

    rows = (
        (await db.execute(select(Notification).where(Notification.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_non_hard_date_deadline_does_not_notify(db, enable_event_driven):
    # deadline_kind != HARD_DATE → nada acontece
    ws = await make_workspace(db)
    await db.commit()

    repo = TaskRepository(db)
    await create_task(
        TaskCreateCommand(
            title="Sem hard date",
            category="Invest",
            priority="S",
            deadline_kind="MONTH",
            deadline_label="este mês",
        ),
        workspace_id=ws.id,
        repo=repo,
        db=db,
    )
    await db.commit()

    rows = (
        (await db.execute(select(Notification).where(Notification.workspace_id == ws.id)))
        .scalars()
        .all()
    )
    assert rows == []
