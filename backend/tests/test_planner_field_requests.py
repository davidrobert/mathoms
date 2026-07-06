"""Telemetria M4 — ``planner_field_requests`` (ADR-206). Persistência idempotente + agregação top-N + endpoint admin."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_field_request import PlannerFieldRequest
from backend.app.models.planner_review import PlannerReview
from backend.app.repositories.planner_field_request_repository import (
    PlannerFieldRequestRepository,
)
from backend.app.services.planner_review_persistence import persist_planner_review
from backend.tests import factories
from backend.tests.helpers.planner_seed import (
    build_e5_artifact,
    build_parecer_artifact,
    build_planner_review,
)

PERSONA_HASH = "b" * 64


@pytest.fixture
def sync_session() -> Generator[Session, None, None]:
    s = SyncSessionLocal()
    try:
        yield s
    finally:
        s.close()


_EMPTY_SUMMARY = {
    "riscos_count": 0,
    "sugestoes_execucao_count": 0,
    "sugestoes_taticas_count": 0,
    "sugestoes_estrategicas_count": 0,
    "metricas_count": 0,
}


def _make_detail() -> dict:
    return {
        "success": True,
        "status": "Gerado",
        "cache_hit": False,
        "tokens": {"in": 5000, "out": 1000},
        "cost_usd": 0.42,
        "latency_ms": 8000,
        "tool_iterations": 2,
        "model_id": "anthropic/claude-sonnet-4-20250514",
        "persona_hash": PERSONA_HASH,
        "manifest_version": "1.0",
        "schema_version": "1.0",
        "tier_at_generation": "premium",
        "parecer_summary": _EMPTY_SUMMARY,
    }


_EMPTY_BUCKETS = {
    "pontos_fortes": [],
    "riscos": [],
    "sugestoes_execucao": [],
    "sugestoes_taticas": [],
    "sugestoes_estrategicas": [],
    "metricas": [],
    "notas_metodologicas": [],
}


def _build_metadata() -> dict:
    return {
        "persona_hash": PERSONA_HASH,
        "manifest_version": "1.0",
        "schema_version": "1.0",
        "model_id": "anthropic/claude-sonnet-4-20250514",
        "tier_at_generation": "premium",
        "generated_at": "2026-05-14T16:00:00+00:00",
    }


def _make_artifact_content(campos: list[dict] | None = None) -> dict:
    content: dict = {
        "version": "1.0",
        "metadata": _build_metadata(),
        "diagnostico_geral": "diagnostico minimo para teste de telemetria de campo faltante.",
        **{k: list(v) for k, v in _EMPTY_BUCKETS.items()},
    }
    if campos is not None:
        content["campos_faltantes_pediria_se_iterasse"] = campos
    return content


async def _make_artifacts(db, workspace, run, *, campos: list[dict] | None = None):
    e5 = PipelineArtifact(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        stage="E5",
        artifact_key="analise_financeira",
        content_json={"narrativas": {}},
    )
    parecer = PipelineArtifact(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        stage="E6-parecer",
        artifact_key="parecer_planejador",
        content_json=_make_artifact_content(campos=campos),
    )
    db.add(e5)
    db.add(parecer)
    await db.flush()
    return e5, parecer


# -----------------------------------------------------------------------
# Persistência
# -----------------------------------------------------------------------


def _field_requests_for_review(sync_session, review_id: str) -> list[PlannerFieldRequest]:
    return list(
        sync_session.execute(
            select(PlannerFieldRequest).where(PlannerFieldRequest.planner_review_id == review_id)
        )
        .scalars()
        .all()
    )


_TWO_CAMPOS = [
    {"field_path": "$.dependentes_irpf.idade", "motivo": "permitiria calcular dedução"},
    {"field_path": "$.investimentos.detalhe_ativos", "motivo": "drill-down de concentração"},
]


def _assert_rows_match_two_campos(rows, workspace_id: str) -> None:
    assert len(rows) == 2
    assert {r.field_path for r in rows} == {
        "$.dependentes_irpf.idade",
        "$.investimentos.detalhe_ativos",
    }
    for r in rows:
        assert r.reason == "llm_declared"
        assert r.workspace_id == workspace_id
        assert r.motivo


@pytest.mark.asyncio
async def test_persist_field_requests_when_campos_present(db, sync_session):
    """Happy path: parecer com ``campos_faltantes_pediria_se_iterasse[]`` gera N rows."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    await _make_artifacts(db, workspace, run, campos=_TWO_CAMPOS)
    await db.commit()
    review_id = persist_planner_review(
        sync_session, workspace_id=workspace.id, run_id=run.id, detail=_make_detail()
    )
    sync_session.commit()
    _assert_rows_match_two_campos(_field_requests_for_review(sync_session, review_id), workspace.id)


@pytest.mark.asyncio
async def test_persist_field_requests_skips_when_campos_absent(db, sync_session):
    """Review sem campo ``campos_faltantes`` → zero rows criados."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    await _make_artifacts(db, workspace, run, campos=None)
    await db.commit()

    persist_planner_review(
        sync_session, workspace_id=workspace.id, run_id=run.id, detail=_make_detail()
    )
    sync_session.commit()

    rows = sync_session.execute(select(PlannerFieldRequest)).scalars().all()
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_persist_field_requests_skips_empty_list(db, sync_session):
    """``campos_faltantes_pediria_se_iterasse: []`` → zero rows (lista vazia)."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    await _make_artifacts(db, workspace, run, campos=[])
    await db.commit()

    persist_planner_review(
        sync_session, workspace_id=workspace.id, run_id=run.id, detail=_make_detail()
    )
    sync_session.commit()

    rows = sync_session.execute(select(PlannerFieldRequest)).scalars().all()
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_persist_field_requests_dedup_intra_batch(db, sync_session):
    """Se LLM emitir paths repetidos no mesmo array, persistência dedupa."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    campos = [
        {"field_path": "$.alertas", "motivo": "verificar lista completa de alertas"},
        {"field_path": "$.alertas", "motivo": "repetido, mesmo path"},
    ]
    await _make_artifacts(db, workspace, run, campos=campos)
    await db.commit()

    persist_planner_review(
        sync_session, workspace_id=workspace.id, run_id=run.id, detail=_make_detail()
    )
    sync_session.commit()

    rows = sync_session.execute(select(PlannerFieldRequest)).scalars().all()
    assert len(rows) == 1
    assert rows[0].field_path == "$.alertas"


_AUDIT_ENTRIES = [
    {
        "field_path": "$.patrimonio.bruto",
        "motivo": "detalhar composição [removido: resolve não-nulo]",
        "reason": "field_request_spurious",
    },
    {
        "field_path": "$.composicao_familiar.dependentes",
        "motivo": "quantos dependentes [reanotado: dado presente em $.irpf_kpis.dependentes]",
        "reason": "field_request_wrong_path",
        "alias_path": "$.irpf_kpis.dependentes",
    },
]


def _assert_rows_match_3_vias(rows) -> None:
    by_path = {r.field_path: r for r in rows}
    assert len(rows) == 3
    assert by_path["$.protecao_patrimonial.apolices"].reason == "llm_declared"
    assert by_path["$.patrimonio.bruto"].reason == "field_request_spurious"
    wrong = by_path["$.composicao_familiar.dependentes"]
    assert wrong.reason == "field_request_wrong_path"
    assert "$.irpf_kpis.dependentes" in wrong.motivo


@pytest.mark.asyncio
async def test_persist_field_requests_includes_3_vias_audit_from_meta(db, sync_session):
    """A28.l11: entradas removidas pelo filtro 3-vias (em ``_meta.field_request_audit``)
    persistem com reason spurious/wrong_path; a mantida persiste como llm_declared."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    campos = [{"field_path": "$.protecao_patrimonial.apolices", "motivo": "apólices vigentes"}]
    _, parecer = await _make_artifacts(db, workspace, run, campos=campos)
    parecer.content_json = {
        **parecer.content_json,
        "_meta": {"field_request_audit": list(_AUDIT_ENTRIES)},
    }
    await db.commit()

    review_id = persist_planner_review(
        sync_session, workspace_id=workspace.id, run_id=run.id, detail=_make_detail()
    )
    sync_session.commit()
    _assert_rows_match_3_vias(_field_requests_for_review(sync_session, review_id))


def _persist_twice(sync_session, workspace_id: str, run_id: str) -> tuple[str, str]:
    """Helper: invoca persist 2x e retorna (first_id, second_id)."""
    first_id = persist_planner_review(
        sync_session, workspace_id=workspace_id, run_id=run_id, detail=_make_detail()
    )
    sync_session.commit()
    second_id = persist_planner_review(
        sync_session, workspace_id=workspace_id, run_id=run_id, detail=_make_detail()
    )
    sync_session.commit()
    return first_id, second_id


@pytest.mark.asyncio
async def test_persist_field_requests_idempotent_with_review_persistence(db, sync_session):
    """Re-execução do stage no mesmo run = no-op (review idempotente; field_requests também)."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    campos = [{"field_path": "$.goals.if_meta", "motivo": "permitiria calcular trajetória"}]
    await _make_artifacts(db, workspace, run, campos=campos)
    await db.commit()

    first_id, second_id = _persist_twice(sync_session, workspace.id, run.id)
    assert first_id == second_id
    rows = sync_session.execute(select(PlannerFieldRequest)).scalars().all()
    # Idempotente: review pré-existente curto-circuita → field_requests NÃO duplicam.
    assert len(rows) == 1


# -----------------------------------------------------------------------
# Repository — top N agregado
# -----------------------------------------------------------------------


async def _seed_review(db, workspace, run) -> PlannerReview:
    """Cria E5 + parecer artifacts + PlannerReview correspondente — fixture builder."""
    e5 = build_e5_artifact(workspace.id, run.id)
    parecer = build_parecer_artifact(workspace.id, run.id, content_json=_make_artifact_content())
    db.add_all([e5, parecer])
    await db.flush()
    review = build_planner_review(
        workspace.id,
        run.id,
        parecer_artifact_id=parecer.id,
        e5_artifact_id=e5.id,
        persona_hash=PERSONA_HASH,
    )
    db.add(review)
    await db.flush()
    return review


def _add_field_request(db, *, workspace_id, review_id, path, created_at=None):
    """Helper insert de field request com created_at opcional (defaut now())."""
    db.add(
        PlannerFieldRequest(
            workspace_id=workspace_id,
            planner_review_id=review_id,
            field_path=path,
            motivo="t",
            reason="llm_declared",
            **({"created_at": created_at} if created_at else {}),
        )
    )


@pytest.mark.asyncio
async def test_top_requested_fields_groups_by_path(db):
    """3 reviews, 5 rows totais, top-N agrupa por path com freq desc."""
    workspace = await factories.make_workspace(db)
    runs = [await factories.make_run(db, workspace=workspace) for _ in range(3)]
    reviews = [await _seed_review(db, workspace, r) for r in runs]
    # path A: 3 reviews; path B: 2 reviews; path C: 1 review.
    paths_by_review = [["$.a", "$.b", "$.c"], ["$.a", "$.b"], ["$.a"]]
    for review, paths in zip(reviews, paths_by_review):
        for p in paths:
            _add_field_request(db, workspace_id=workspace.id, review_id=review.id, path=p)
    await db.commit()

    top = await PlannerFieldRequestRepository(db).top_requested_fields(days=30, limit=10)
    assert [t.field_path for t in top] == ["$.a", "$.b", "$.c"]
    assert top[0].frequency == 3
    assert top[1].frequency == 2
    assert top[2].frequency == 1


@pytest.mark.asyncio
async def test_top_requested_fields_respects_days_window(db):
    """Rows fora da janela ``days`` não entram na agregação."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    review = await _seed_review(db, workspace, run)
    old = datetime.now(timezone.utc) - timedelta(days=60)
    _add_field_request(
        db, workspace_id=workspace.id, review_id=review.id, path="$.old", created_at=old
    )
    _add_field_request(db, workspace_id=workspace.id, review_id=review.id, path="$.fresh")
    await db.commit()

    top = await PlannerFieldRequestRepository(db).top_requested_fields(days=30, limit=10)
    paths = {t.field_path for t in top}
    assert "$.fresh" in paths
    assert "$.old" not in paths
