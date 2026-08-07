"""A40.l18 · ADR-357 — o relatório só afirma "sem pendências" se o run entregou tudo."""

from __future__ import annotations

import uuid

import pytest

from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.report_run_outcome import (
    ReportRunOutcome,
    outcome_for_report,
    run_outcomes_for,
)


async def _run(session, status: PipelineRunStatus, *, degraded_stage: str | None = None) -> str:
    uid, wid = str(uuid.uuid4()), str(uuid.uuid4())
    session.add(User(id=uid, email=f"ro-{uid[:8]}@t.co", hashed_password="x", full_name="T"))
    session.add(Workspace(id=wid, name="WS", owner_id=uid))
    run = PipelineRun(id=str(uuid.uuid4()), workspace_id=wid, status=status)
    session.add(run)
    if degraded_stage:
        session.add(
            PipelineStageLog(
                id=str(uuid.uuid4()),
                pipeline_run_id=run.id,
                stage=degraded_stage,
                status=PipelineStageStatus.degraded,
            )
        )
    await session.commit()
    return run.id


@pytest.mark.asyncio
async def test_run_completo_e_limpo_autoriza_a_afirmacao(db):
    rid = await _run(db, PipelineRunStatus.completed)
    outcomes = await run_outcomes_for(db, [rid])
    assert outcomes[rid] is ReportRunOutcome.complete


@pytest.mark.asyncio
async def test_partial_failure_nao_autoriza(db):
    rid = await _run(
        db,
        PipelineRunStatus.partial_failure,
        degraded_stage="review_finances_holistic",
    )
    outcomes = await run_outcomes_for(db, [rid])
    assert outcomes[rid] is ReportRunOutcome.with_gap


@pytest.mark.asyncio
async def test_completed_com_stage_degradado_nao_autoriza(db):
    """Predicado POSITIVO: `completed` não basta, o run precisa estar limpo."""
    # Alcança o run que o `resume`/redelivery finalizou `completed` com um
    # `stage_log` degradado no banco — se o predicado fosse
    # `status == partial_failure`, este caso voltaria a afirmar "sem pendências".
    rid = await _run(db, PipelineRunStatus.completed, degraded_stage="generate_narratives")
    outcomes = await run_outcomes_for(db, [rid])
    assert outcomes[rid] is ReportRunOutcome.with_gap


@pytest.mark.asyncio
async def test_run_cancelado_com_relatorio_nao_autoriza(db):
    """Cancelar depois de `analyze_finances` já gera relatório — e ele não está limpo."""
    # É o caso que a polaridade negativa deixaria passar: `cancelled` não é
    # `partial_failure`, então um gate escrito pelo negativo afirmaria
    # "sem pendências" num run que nem terminou.
    rid = await _run(db, PipelineRunStatus.cancelled)
    outcomes = await run_outcomes_for(db, [rid])
    assert outcomes[rid] is ReportRunOutcome.with_gap


@pytest.mark.asyncio
async def test_run_purgado_e_indeterminado(db):
    """`reports.pipeline_run_id` é `ondelete=SET NULL` — sem evidência, fail-closed."""
    assert outcome_for_report(None, {}) is ReportRunOutcome.unknown
    assert outcome_for_report("nao-existe", {}) is ReportRunOutcome.unknown
    assert await run_outcomes_for(db, []) == {}
    assert await run_outcomes_for(db, [None]) == {}  # type: ignore[list-item]


@pytest.mark.asyncio
async def test_resolve_lote_sem_uma_query_por_relatorio(db):
    """`list_reports` serializa N relatórios — o resolvedor é batch por construção."""
    limpo = await _run(db, PipelineRunStatus.completed)
    lacuna = await _run(db, PipelineRunStatus.partial_failure, degraded_stage="validate_cross")
    outcomes = await run_outcomes_for(db, [limpo, lacuna])
    assert outcomes == {
        limpo: ReportRunOutcome.complete,
        lacuna: ReportRunOutcome.with_gap,
    }
