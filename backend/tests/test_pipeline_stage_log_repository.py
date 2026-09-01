"""Tests — ``PipelineStageLogRepository.get_median_durations_for_workspace`` (ADR-119)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.models import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
    User,
    Workspace,
)
from backend.app.repositories.pipeline_stage_log_repository import (
    PipelineStageLogRepository,
)


async def _make_workspace(db: AsyncSession, name: str = "WS") -> str:
    user = User(
        email=f"u{name}@t.com".replace(" ", ""),
        hashed_password=hash_password("p"),
        full_name=name,
    )
    db.add(user)
    await db.flush()
    ws = Workspace(name=name, owner_id=user.id)
    db.add(ws)
    await db.flush()
    return ws.id


async def _seed_stage_log(
    db: AsyncSession,
    ws_id: str,
    *,
    stage: str,
    duration_ms: int | None,
    status: PipelineStageStatus = PipelineStageStatus.completed,
    run_status: PipelineRunStatus = PipelineRunStatus.completed,
    started_offset_sec: int = 0,
    output_summary: dict | None = None,
) -> None:
    run = PipelineRun(workspace_id=ws_id, status=run_status)
    db.add(run)
    await db.flush()
    log = PipelineStageLog(
        pipeline_run_id=run.id,
        stage=stage,
        status=status,
        duration_ms=duration_ms,
        started_at=datetime.now(timezone.utc) + timedelta(seconds=started_offset_sec),
        output_summary=output_summary,
    )
    db.add(log)
    await db.flush()


def _median_via_sync(
    sync_session: Session, ws_id: str, *, limit_per_stage: int = 20
) -> dict[str, int]:
    # AsyncSession.run_sync(fn) invoca fn com a Session síncrona subjacente.
    return PipelineStageLogRepository(sync_session).get_median_durations_for_workspace(
        ws_id, limit_per_stage=limit_per_stage
    )


@pytest.mark.asyncio
async def test_returns_median_with_3_or_more_samples(db: AsyncSession):
    ws_id = await _make_workspace(db)
    for dur in [1000, 2000, 3000]:
        await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=dur)
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id))
    assert result == {"E1.5": 2000}


@pytest.mark.asyncio
async def test_omits_stages_with_fewer_than_3_samples(db: AsyncSession):
    ws_id = await _make_workspace(db)
    await _seed_stage_log(db, ws_id, stage="E1", duration_ms=500)
    await _seed_stage_log(db, ws_id, stage="E1", duration_ms=700)
    await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=1000)
    await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=2000)
    await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=3000)
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id))
    assert "E1" not in result
    assert result == {"E1.5": 2000}


@pytest.mark.asyncio
async def test_excludes_non_completed_stage_logs(db: AsyncSession):
    ws_id = await _make_workspace(db)
    for dur in [1000, 2000, 3000]:
        await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=dur)
    await _seed_stage_log(
        db,
        ws_id,
        stage="E1.5",
        duration_ms=999_999,
        status=PipelineStageStatus.failed,
    )
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id))
    assert result["E1.5"] == 2000


@pytest.mark.asyncio
async def test_excludes_null_duration(db: AsyncSession):
    ws_id = await _make_workspace(db)
    for dur in [1000, 2000, 3000]:
        await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=dur)
    await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=None)
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id))
    assert result["E1.5"] == 2000


@pytest.mark.asyncio
async def test_scoped_per_workspace(db: AsyncSession):
    ws_a = await _make_workspace(db, name="A")
    ws_b = await _make_workspace(db, name="B")
    for dur in [1000, 2000, 3000]:
        await _seed_stage_log(db, ws_a, stage="E1.5", duration_ms=dur)
    for dur in [500, 600, 700]:
        await _seed_stage_log(db, ws_b, stage="E1.5", duration_ms=dur)
    await db.commit()

    results = await db.run_sync(lambda s: (_median_via_sync(s, ws_a), _median_via_sync(s, ws_b)))
    assert results[0] == {"E1.5": 2000}
    assert results[1] == {"E1.5": 600}


@pytest.mark.asyncio
async def test_empty_when_no_completed_runs(db: AsyncSession):
    ws_id = await _make_workspace(db)
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id))
    assert result == {}


@pytest.mark.asyncio
async def test_respects_limit_per_stage_window(db: AsyncSession):
    """Amostras além de limit_per_stage são descartadas (janela 'últimos N')."""
    ws_id = await _make_workspace(db)
    for i in range(30):
        # mais recentes = valores altos; o corte em N=20 pega os mais recentes.
        await _seed_stage_log(
            db,
            ws_id,
            stage="E1.5",
            duration_ms=10_000 + i * 100,
            started_offset_sec=i,
        )
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id, limit_per_stage=20))
    # Últimas 20 (started_offset_sec 10..29): duração 11000..12900,
    # mediana = média dos 2 centrais (11950, 12000) = 11950
    assert result["E1.5"] == 11950


# --- A42.l22: no-op auto-declarado sai da população da mediana -----------------
#
# `{"skipped": True}` grava `completed` de propósito (`_STAGE_STATUS_BY_OUTCOME`,
# ADR-357 §2) — logo passa pelo filtro de status. Mas ele roda em milissegundos e
# a execução real leva minutos, e a ETA só é LIDA no ramo em que o stage
# executa de verdade (os early-returns de `extract_baseline`/`extract_irpf_full`
# antecedem a leitura de `ctx.stage_duration_estimates`).


@pytest.mark.asyncio
async def test_excludes_declared_noop_from_median(db: AsyncSession):
    ws_id = await _make_workspace(db)
    for dur in [300_000, 310_000, 320_000]:
        await _seed_stage_log(db, ws_id, stage="extract_baseline", duration_ms=dur)
    for dur in [5, 6, 7]:
        await _seed_stage_log(
            db,
            ws_id,
            stage="extract_baseline",
            duration_ms=dur,
            output_summary={"skipped": True, "reason": "No LLM config — free tier"},
        )
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id))
    # Sem o filtro a mediana das 6 amostras seria 150_003 — 51% otimista.
    assert result == {"extract_baseline": 310_000}


@pytest.mark.asyncio
async def test_keeps_rows_that_do_not_declare_skip(db: AsyncSession):
    """`skipped: false` e chave ausente são execução real — não saem da amostra."""
    ws_id = await _make_workspace(db)
    await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=1000, output_summary=None)
    await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=2000, output_summary={"files": 3})
    await _seed_stage_log(
        db, ws_id, stage="E1.5", duration_ms=3000, output_summary={"skipped": False}
    )
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id))
    assert result == {"E1.5": 2000}


@pytest.mark.asyncio
async def test_noop_rows_do_not_consume_the_window(db: AsyncSession):
    """A janela é 'últimas N execuções reais', não 'últimas N linhas'."""
    ws_id = await _make_workspace(db)
    for i in range(3):
        await _seed_stage_log(db, ws_id, stage="E1.5", duration_ms=1000, started_offset_sec=i)
    # Mais recentes que as reais: sem o filtro, encheriam a janela sozinhas.
    for i in range(3):
        await _seed_stage_log(
            db,
            ws_id,
            stage="E1.5",
            duration_ms=9,
            started_offset_sec=10 + i,
            output_summary={"skipped": True},
        )
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id, limit_per_stage=3))
    assert result == {"E1.5": 1000}


@pytest.mark.asyncio
async def test_noop_rows_do_not_satisfy_the_minimum_sample_count(db: AsyncSession):
    """Stage que só no-opou não tem amostra: omitido, em vez de estimar 9ms."""
    ws_id = await _make_workspace(db)
    for i in range(5):
        await _seed_stage_log(
            db,
            ws_id,
            stage="extract_comprovantes_bens",
            duration_ms=9,
            started_offset_sec=i,
            output_summary={"skipped": True},
        )
    await db.commit()

    result = await db.run_sync(lambda conn: _median_via_sync(conn, ws_id))
    assert result == {}
