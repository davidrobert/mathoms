"""REL-03 — idempotência de Report sob redelivery do Celery.

Dois mecanismos:
1. Índice único parcial ``(workspace_id, pipeline_run_id)`` em ``reports``
   transforma o Report duplicado (run re-executado por redelivery) em
   ``IntegrityError`` — backstop à prova de corrida.
2. Guarda de estado terminal em ``_mark_run_started``: redelivery de um run
   já finalizado não re-executa o pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.report import Report
from backend.app.tasks.pipeline_task import _mark_run_started
from backend.tests.factories.builders import make_user, make_workspace


async def _seed_run(db: AsyncSession, status: PipelineRunStatus) -> tuple[str, str]:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = PipelineRun(workspace_id=ws.id, status=status)
    db.add(run)
    await db.commit()
    return ws.id, run.id


def _report(ws_id: str, run_id: str | None) -> Report:
    return Report(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        title=f"Relatório {datetime.now(timezone.utc).isoformat()}",
    )


@pytest.mark.asyncio
async def test_duplicate_report_for_same_run_is_rejected(db: AsyncSession) -> None:
    ws_id, run_id = await _seed_run(db, PipelineRunStatus.completed)
    db.add(_report(ws_id, run_id))
    await db.commit()

    db.add(_report(ws_id, run_id))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()

    count = await db.scalar(
        select(func.count()).select_from(Report).where(Report.pipeline_run_id == run_id)
    )
    assert count == 1


@pytest.mark.asyncio
async def test_reports_with_null_run_coexist(db: AsyncSession) -> None:
    """Índice é parcial (``WHERE pipeline_run_id IS NOT NULL``): Reports órfãos
    (run hard-deleted → SET NULL) não colidem entre si."""
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    db.add(_report(ws.id, None))
    db.add(_report(ws.id, None))
    await db.commit()

    count = await db.scalar(
        select(func.count()).select_from(Report).where(Report.workspace_id == ws.id)
    )
    assert count == 2


@pytest.mark.asyncio
async def test_mark_run_started_skips_terminal_run(db: AsyncSession) -> None:
    _, run_id = await _seed_run(db, PipelineRunStatus.completed)

    assert _mark_run_started(run_id, "premium", "task-redelivered") is False

    refreshed = (
        await db.execute(
            select(PipelineRun)
            .where(PipelineRun.id == run_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed.status == PipelineRunStatus.completed


@pytest.mark.asyncio
async def test_mark_run_started_allows_running_run_for_crash_recovery(db: AsyncSession) -> None:
    """``running`` NÃO é terminal — redelivery após crash precisa re-entrar."""
    _, run_id = await _seed_run(db, PipelineRunStatus.running)
    assert _mark_run_started(run_id, "premium", "task-recover") is True
