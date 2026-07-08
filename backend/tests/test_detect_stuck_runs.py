"""ADR-172 (W2-T04) — beat task ``fin.detect_stuck_runs``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Notification
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.pipeline.pipeline_failure_reasons import HEARTBEAT_TIMEOUT
from backend.app.tasks.periodic_tasks import detect_stuck_runs
from backend.tests.factories.builders import make_user, make_workspace


def _heartbeat_value(minutes_ago: int | None) -> datetime | None:
    if minutes_ago is None:
        return None
    return datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)


async def _make_run(
    db: AsyncSession,
    *,
    status: PipelineRunStatus,
    heartbeat_minutes_ago: int | None,
    current_stage: str | None = "extract_statements",
) -> PipelineRun:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = PipelineRun(
        workspace_id=ws.id,
        status=status,
        current_stage=current_stage,
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        last_heartbeat_at=_heartbeat_value(heartbeat_minutes_ago),
    )
    db.add(run)
    await db.commit()
    return run


async def _reload(db: AsyncSession, run_id: str) -> PipelineRun:
    return (
        await db.execute(
            select(PipelineRun)
            .where(PipelineRun.id == run_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


@pytest.fixture(autouse=True)
def _silence_publish(monkeypatch):
    monkeypatch.setattr(
        "backend.app.tasks.periodic_tasks.publish_run_failed",
        lambda *_a, **_k: None,
    )


@pytest.mark.asyncio
async def test_stale_heartbeat_marks_run_failed(db: AsyncSession) -> None:
    run = await _make_run(db, status=PipelineRunStatus.running, heartbeat_minutes_ago=30)

    result = detect_stuck_runs.run()
    assert result["detected"] == 1

    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.failed
    assert refreshed.failure_reason == HEARTBEAT_TIMEOUT
    assert refreshed.failed_at_stage == "extract_statements"
    assert refreshed.current_stage is None
    assert refreshed.completed_at is not None


@pytest.mark.asyncio
async def test_stale_heartbeat_creates_notification(db: AsyncSession) -> None:
    run = await _make_run(db, status=PipelineRunStatus.running, heartbeat_minutes_ago=30)

    detect_stuck_runs.run()

    notifs = (
        (
            await db.execute(
                select(Notification).where(Notification.workspace_id == run.workspace_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(notifs) == 1
    assert notifs[0].severity == "error"
    assert notifs[0].source == "pipeline"


@pytest.mark.asyncio
async def test_recent_heartbeat_is_not_flagged(db: AsyncSession) -> None:
    run = await _make_run(db, status=PipelineRunStatus.running, heartbeat_minutes_ago=2)

    assert detect_stuck_runs.run()["detected"] == 0
    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.running
    assert refreshed.failure_reason is None


@pytest.mark.asyncio
async def test_terminal_run_is_not_touched(db: AsyncSession) -> None:
    completed = await _make_run(db, status=PipelineRunStatus.completed, heartbeat_minutes_ago=60)
    cancelled = await _make_run(db, status=PipelineRunStatus.cancelled, heartbeat_minutes_ago=60)

    assert detect_stuck_runs.run()["detected"] == 0
    for run in (completed, cancelled):
        refreshed = await _reload(db, run.id)
        assert refreshed.failure_reason is None


@pytest.mark.asyncio
async def test_run_without_heartbeat_is_skipped(db: AsyncSession) -> None:
    await _make_run(db, status=PipelineRunStatus.running, heartbeat_minutes_ago=None)
    assert detect_stuck_runs.run()["detected"] == 0


@pytest.mark.asyncio
async def test_idempotency_second_run_is_noop(db: AsyncSession) -> None:
    await _make_run(db, status=PipelineRunStatus.running, heartbeat_minutes_ago=30)
    assert detect_stuck_runs.run()["detected"] == 1
    assert detect_stuck_runs.run()["detected"] == 0


@pytest.mark.asyncio
async def test_threshold_override_via_env(db: AsyncSession, monkeypatch) -> None:
    monkeypatch.setenv("MATHOMS_STUCK_RUN_THRESHOLD_MINUTES", "5")
    await _make_run(db, status=PipelineRunStatus.running, heartbeat_minutes_ago=10)
    assert detect_stuck_runs.run()["detected"] == 1
