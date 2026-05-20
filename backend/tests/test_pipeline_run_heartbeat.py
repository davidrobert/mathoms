"""ADR-172 (W2-T04) — heartbeat write-path em ``pipeline_task``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.tasks.pipeline_task import _mark_run_started, _record_stage_running
from backend.tests.factories.builders import make_user, make_workspace


async def _seed_pending_run(db: AsyncSession) -> str:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = PipelineRun(
        workspace_id=ws.id,
        status=PipelineRunStatus.pending,
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        last_heartbeat_at=None,
    )
    db.add(run)
    await db.commit()
    return run.id


async def _reload(db: AsyncSession, run_id: str) -> PipelineRun:
    return (
        await db.execute(
            select(PipelineRun)
            .where(PipelineRun.id == run_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


@pytest.mark.asyncio
async def test_mark_run_started_sets_heartbeat(db: AsyncSession) -> None:
    run_id = await _seed_pending_run(db)
    before = datetime.now(timezone.utc)

    assert _mark_run_started(run_id, "premium", "task-abc") is True

    await db.commit()
    refreshed = await _reload(db, run_id)
    assert refreshed.status == PipelineRunStatus.running
    assert refreshed.last_heartbeat_at is not None
    assert refreshed.last_heartbeat_at >= before


@pytest.mark.asyncio
async def test_record_stage_running_updates_heartbeat(db: AsyncSession, monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.tasks.pipeline_task.publish_stage_started",
        lambda *_a, **_k: None,
    )
    run_id = await _seed_pending_run(db)
    _mark_run_started(run_id, "premium", "task-xyz")
    stage_started_at = datetime.now(timezone.utc) + timedelta(seconds=5)

    _record_stage_running(
        run_id=run_id,
        stage_name="extract_statements",
        log_id="log-1",
        stage_started_at=stage_started_at,
        progress_pct=10,
    )

    refreshed = await _reload(db, run_id)
    assert refreshed.current_stage == "extract_statements"
    assert refreshed.last_heartbeat_at == stage_started_at
