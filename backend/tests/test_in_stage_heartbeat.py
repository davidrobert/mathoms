"""A37.l12 (CTO-06) — heartbeat in-stage no loop de documentos.

Critério de aceite (fake clock via ``last_heartbeat_at`` retro-datado):
stage de 20 min COM batida in-stage → watchdog não flipa; SEM batida →
flipa (comportamento ADR-172 preservado para travas reais). Batida é DB
write CAS (``WHERE status='running'``) — nunca thread/timer (ADR-111),
nunca read-modify-write cross-worker (anti flip-flop).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.pipeline.heartbeat import record_in_stage_heartbeat
from backend.app.services.pipeline.pipeline_failure_reasons import HEARTBEAT_TIMEOUT
from backend.app.tasks.periodic_tasks import detect_stuck_runs
from backend.tests.factories.builders import make_user, make_workspace
from pipeline.live_progress import emit_item_progress


async def _make_run(
    db: AsyncSession,
    *,
    status: PipelineRunStatus = PipelineRunStatus.running,
    heartbeat_minutes_ago: int = 20,
) -> PipelineRun:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = PipelineRun(
        workspace_id=ws.id,
        status=status,
        current_stage="extract_with_llm",
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        last_heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=heartbeat_minutes_ago),
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


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _emit_doc_progress(run_id: str, items_done: int, items_total: int = 8) -> None:
    emit_item_progress(
        run_id,
        "extract_with_llm",
        current_item=f"doc_{items_done}.pdf",
        items_done=items_done,
        items_total=items_total,
        phase="preparing",
    )


@pytest.fixture(autouse=True)
def _silence_publishes(monkeypatch):
    monkeypatch.setattr(
        "backend.app.tasks.periodic_tasks.publish_run_failed",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "backend.app.services.pipeline.events.publish_item_progress",
        lambda *_a, **_k: None,
    )


@pytest.mark.asyncio
async def test_long_stage_with_in_stage_beats_survives_watchdog(db: AsyncSession) -> None:
    """Stage de 20 min COM batida in-stage no loop de docs → watchdog não flipa."""
    run = await _make_run(db, heartbeat_minutes_ago=20)
    before = datetime.now(timezone.utc)

    _emit_doc_progress(run.id, items_done=3)

    assert detect_stuck_runs.run()["detected"] == 0
    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.running
    assert refreshed.failure_reason is None
    assert _as_utc(refreshed.last_heartbeat_at) >= before


@pytest.mark.asyncio
async def test_long_stage_without_beats_flips(db: AsyncSession) -> None:
    """SEM batida in-stage o comportamento atual é preservado: trava real flipa."""
    run = await _make_run(db, heartbeat_minutes_ago=20)

    assert detect_stuck_runs.run()["detected"] == 1
    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.failed
    assert refreshed.failure_reason == HEARTBEAT_TIMEOUT


@pytest.mark.asyncio
async def test_heartbeat_cas_does_not_resurrect_flipped_run(db: AsyncSession) -> None:
    """Anti flip-flop: run já flipado pelo watchdog não renova heartbeat nem volta a running."""
    run = await _make_run(db, status=PipelineRunStatus.failed, heartbeat_minutes_ago=20)
    stale = run.last_heartbeat_at

    assert record_in_stage_heartbeat(run.id) is False

    refreshed = await _reload(db, run.id)
    assert refreshed.status == PipelineRunStatus.failed
    assert _as_utc(refreshed.last_heartbeat_at) == _as_utc(stale)


@pytest.mark.asyncio
async def test_heartbeat_cas_updates_running_run(db: AsyncSession) -> None:
    run = await _make_run(db, heartbeat_minutes_ago=20)
    before = datetime.now(timezone.utc)

    assert record_in_stage_heartbeat(run.id) is True

    refreshed = await _reload(db, run.id)
    assert _as_utc(refreshed.last_heartbeat_at) >= before


@pytest.mark.asyncio
async def test_heartbeat_cadence_every_n_docs(db: AsyncSession, monkeypatch) -> None:
    """Env ``MATHOMS_HEARTBEAT_EVERY_N_DOCS=3`` → batida só em items_done múltiplo de 3."""
    monkeypatch.setenv("MATHOMS_HEARTBEAT_EVERY_N_DOCS", "3")
    beats: list[str] = []
    monkeypatch.setattr(
        "backend.app.services.pipeline.heartbeat.record_in_stage_heartbeat",
        lambda run_id: beats.append(run_id) or True,
    )

    for items_done in range(6):
        _emit_doc_progress("run-cadence", items_done=items_done)

    assert len(beats) == 2  # items_done 0 e 3


@pytest.mark.asyncio
async def test_heartbeat_cadence_invalid_env_falls_back_to_default(
    db: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setenv("MATHOMS_HEARTBEAT_EVERY_N_DOCS", "not-a-number")
    beats: list[str] = []
    monkeypatch.setattr(
        "backend.app.services.pipeline.heartbeat.record_in_stage_heartbeat",
        lambda run_id: beats.append(run_id) or True,
    )

    for items_done in range(3):
        _emit_doc_progress("run-fallback", items_done=items_done)

    assert len(beats) == 3  # default N=1: toda emissão bate


@pytest.mark.asyncio
async def test_no_heartbeat_without_run_id(monkeypatch) -> None:
    """CLI/testes (``pipeline_run_id`` ausente) → no-op, sem DB write."""
    beats: list[str] = []
    monkeypatch.setattr(
        "backend.app.services.pipeline.heartbeat.record_in_stage_heartbeat",
        lambda run_id: beats.append(run_id) or True,
    )

    emit_item_progress(
        None,
        "extract_with_llm",
        current_item="doc.pdf",
        items_done=0,
        items_total=1,
        phase="preparing",
    )

    assert beats == []


@pytest.mark.asyncio
async def test_heartbeat_fires_even_if_ws_publish_fails(db: AsyncSession, monkeypatch) -> None:
    """Batida não depende do publish WS — Redis fora não pode matar o heartbeat."""

    def _boom(*_a, **_k):
        raise RuntimeError("redis down")

    monkeypatch.setattr("backend.app.services.pipeline.events.publish_item_progress", _boom)
    run = await _make_run(db, heartbeat_minutes_ago=20)
    before = datetime.now(timezone.utc)

    _emit_doc_progress(run.id, items_done=0)

    refreshed = await _reload(db, run.id)
    assert _as_utc(refreshed.last_heartbeat_at) >= before
