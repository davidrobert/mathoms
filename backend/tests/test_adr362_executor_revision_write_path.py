"""ADR-362 — write-path da revisão do executor em ``pipeline_stage_logs``."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core import config as core_config
from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.tasks.pipeline_task import _record_stage_running, _record_stage_skip
from backend.tests.factories.builders import make_user, make_workspace


async def _seed_run(db: AsyncSession) -> str:
    user = await make_user(db)
    ws = await make_workspace(db, owner=user)
    run = PipelineRun(
        workspace_id=ws.id,
        status=PipelineRunStatus.running,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    return run.id


async def _logs(db: AsyncSession, run_id: str) -> list[PipelineStageLog]:
    return list(
        (
            await db.execute(
                select(PipelineStageLog)
                .where(PipelineStageLog.pipeline_run_id == run_id)
                .order_by(PipelineStageLog.started_at)
                .execution_options(populate_existing=True)
            )
        ).scalars()
    )


@pytest.fixture
def pinned_revision(monkeypatch):
    """Pina a revisão como o launch faria, sem depender do git da máquina."""

    def _pin(value: str) -> None:
        monkeypatch.setattr(core_config.settings, "BUILD_SHA", value, raising=False)

    return _pin


@pytest.mark.asyncio
async def test_stage_que_crashou_carrega_a_revisao(db: AsyncSession, pinned_revision) -> None:
    """Row que nunca atinge terminal é onde a atribuição vale MAIS."""
    # Mutação que mata: mover a escrita para `_record_stage_result` ⇒ NULL aqui,
    # exatamente nas rows dos runs que crasharam.
    pinned_revision("aaaaaaaaaaaa")
    run_id = await _seed_run(db)

    _record_stage_running(run_id, "reconcile_transactions", str(uuid.uuid4()), _now(), 10)

    rows = await _logs(db, run_id)
    assert len(rows) == 1
    assert rows[0].status == PipelineStageStatus.running
    assert rows[0].executor_revision == "aaaaaaaaaaaa"


@pytest.mark.asyncio
async def test_stage_pulado_carrega_a_revisao(db: AsyncSession, pinned_revision) -> None:
    """O 2º sítio de INSERT — construtor campo-a-campo perde campo novo em silêncio."""
    pinned_revision("bbbbbbbbbbbb")
    run_id = await _seed_run(db)

    _record_stage_skip(
        run_id,
        "review_finances_holistic",
        str(uuid.uuid4()),
        _now(),
        should_skip_free=True,
        progress_pct=90,
    )

    rows = await _logs(db, run_id)
    assert len(rows) == 1
    assert rows[0].status == PipelineStageStatus.skipped_free_tier
    assert rows[0].executor_revision == "bbbbbbbbbbbb"


@pytest.mark.asyncio
async def test_execucao_mista_preserva_duas_revisoes(db: AsyncSession, pinned_revision) -> None:
    """Resume com deploy no meio ⇒ o run tem N revisões, não um escalar."""
    # Mutação que mata: first-writer-wins num campo do run ⇒ COUNT(DISTINCT) == 1.
    run_id = await _seed_run(db)
    pinned_revision("aaaaaaaaaaaa")
    _record_stage_running(run_id, "reconcile_transactions", str(uuid.uuid4()), _now(), 10)
    pinned_revision("bbbbbbbbbbbb")
    _record_stage_running(run_id, "analyze_finances", str(uuid.uuid4()), _now(), 50)

    revisions = {r.executor_revision for r in await _logs(db, run_id)}
    assert revisions == {"aaaaaaaaaaaa", "bbbbbbbbbbbb"}


@pytest.mark.asyncio
async def test_sha_de_40_chars_nao_estoura_a_coluna(db: AsyncSession, pinned_revision) -> None:
    """`${{ github.sha }}` tem 40 chars; `varchar` rejeita INSERT acima do limite."""
    pinned_revision(f"{'a' * 40}-dirty")
    run_id = await _seed_run(db)

    _record_stage_running(run_id, "reconcile_transactions", str(uuid.uuid4()), _now(), 10)

    rows = await _logs(db, run_id)
    assert rows[0].executor_revision == "a" * 12 + "-dirty"
    assert len(rows[0].executor_revision) <= 48


@pytest.mark.asyncio
async def test_sem_a_env_a_coluna_fica_null_e_o_stage_roda(
    db: AsyncSession, pinned_revision
) -> None:
    """Degradação: ausência é NULL, nunca a string "unknown", e nada quebra."""
    pinned_revision("")
    run_id = await _seed_run(db)

    _record_stage_running(run_id, "reconcile_transactions", str(uuid.uuid4()), _now(), 10)

    rows = await _logs(db, run_id)
    assert rows[0].executor_revision is None


@pytest.mark.asyncio
async def test_atribuicao_total_de_output_summary_nao_apaga_a_revisao(
    db: AsyncSession, pinned_revision
) -> None:
    """Coluna > chave em JSON: é o que justifica a migration em vez de reusar `output_summary`."""
    # Os 3 caminhos terminais de `pipeline_task` fazem
    # `stage_log.output_summary = result.detail` — atribuição TOTAL. Uma chave
    # posta no INSERT seria apagada; a coluna sobrevive.
    pinned_revision("cccccccccccc")
    run_id = await _seed_run(db)
    _record_stage_running(run_id, "reconcile_transactions", str(uuid.uuid4()), _now(), 10)

    row = (await _logs(db, run_id))[0]
    row.output_summary = {"validation": "ok"}  # exatamente o que o terminal faz
    row.status = PipelineStageStatus.completed
    await db.commit()

    refreshed = (await _logs(db, run_id))[0]
    assert refreshed.output_summary == {"validation": "ok"}
    assert refreshed.executor_revision == "cccccccccccc"


def _now() -> datetime:
    return datetime.now(timezone.utc)
