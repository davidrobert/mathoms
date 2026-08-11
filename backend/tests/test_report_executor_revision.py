"""Colofão do relatório expõe a revisão (ADR-362) do stage E5 do run — nunca fabricada."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.application.report.get_report import get_report
from backend.app.services.report_executor_revision import (
    analysis_revisions_for,
    revision_for_report,
)
from backend.tests.factories.builders import (
    make_report,
    make_run,
    make_stage_log,
    make_workspace,
)

_T0 = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_detail_expoe_revisao_do_stage_e5(db):
    ws = await make_workspace(db)
    run = await make_run(db, workspace=ws)
    await make_stage_log(db, run=run, stage="analyze_finances", executor_revision="abc123def456")
    report = await make_report(db, workspace=ws, pipeline_run=run)

    response = await get_report(ws.id, report.id, db=db)
    assert response.executor_revision == "abc123def456"


async def _run_com_logs_e5(db, *revisions: str | None) -> str:
    ws = await make_workspace(db)
    run = await make_run(db, workspace=ws)
    for i, revision in enumerate(revisions):
        await make_stage_log(
            db,
            run=run,
            stage="analyze_finances",
            executor_revision=revision,
            started_at=_T0 + timedelta(minutes=5 * i),
        )
    return run.id


@pytest.mark.asyncio
async def test_stage_log_mais_recente_vence(db):
    """Resume re-executa E5: vale a revisão do log mais novo."""
    rid = await _run_com_logs_e5(db, "aaa111", "bbb222")
    assert (await analysis_revisions_for(db, [rid]))[rid] == "bbb222"


# Mostrar a revisão antiga num run cujo E5 mais recente não declarou seria
# fabricar proveniência (regra anti-backfill da ADR-362).
@pytest.mark.asyncio
async def test_log_mais_recente_sem_revisao_vence_e_da_none(db):
    rid = await _run_com_logs_e5(db, "aaa111", None)
    assert (await analysis_revisions_for(db, [rid]))[rid] is None


@pytest.mark.asyncio
async def test_stage_legado_e5_tambem_e_consultado(db):
    ws = await make_workspace(db)
    run = await make_run(db, workspace=ws)
    await make_stage_log(db, run=run, stage="E5", executor_revision="ccc333")
    assert (await analysis_revisions_for(db, [run.id]))[run.id] == "ccc333"


@pytest.mark.asyncio
async def test_sem_evidencia_e_none_nunca_fabricado(db):
    """Run sem log E5, run purgado (FK SET NULL) e lote vazio → None/{}, sem KeyError."""
    ws = await make_workspace(db)
    run = await make_run(db, workspace=ws)
    await make_stage_log(db, run=run, stage="reconcile_transactions", executor_revision="ddd444")

    revisions = await analysis_revisions_for(db, [run.id])
    assert revisions[run.id] is None

    assert revision_for_report(None, revisions) is None
    assert revision_for_report("run-purgado", revisions) is None
    assert await analysis_revisions_for(db, []) == {}
    assert await analysis_revisions_for(db, [None]) == {}


@pytest.mark.asyncio
async def test_resolve_lote_sem_uma_query_por_relatorio(db):
    ws = await make_workspace(db)
    com = await make_run(db, workspace=ws)
    sem = await make_run(db, workspace=ws)
    await make_stage_log(db, run=com, stage="analyze_finances", executor_revision="eee555")

    revisions = await analysis_revisions_for(db, [com.id, sem.id])
    assert revisions == {com.id: "eee555", sem.id: None}
