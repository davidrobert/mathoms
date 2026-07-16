"""Persistência atômica do PlannerReview pós-stage (ADR-199 / ADR-204 / ADR-208)."""

from __future__ import annotations

from typing import Generator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_review import PlannerReview
from backend.app.models.suggestion import Suggestion
from backend.app.services.planner_review_persistence import (
    persist_after_stage_success,
    persist_planner_review,
)
from backend.tests import factories

PERSONA_HASH = "a" * 64


@pytest.fixture
def sync_session() -> Generator[Session, None, None]:
    """Sessão SQLAlchemy sync — espelha SyncSessionLocal usado pelo Celery worker."""
    s = SyncSessionLocal()
    try:
        yield s
    finally:
        s.close()


def make_detail() -> dict:
    """Espelha o dict retornado pelo `_success_return` do stage."""
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
        "parecer_summary": {
            "riscos_count": 1,
            "sugestoes_execucao_count": 1,
            "sugestoes_taticas_count": 0,
            "sugestoes_estrategicas_count": 0,
            "metricas_count": 0,
        },
    }


def _make_sugestao_with_impacto() -> dict:
    return {
        "prioridade": "P0",
        "acao": "contratar seguro de vida",
        "impacto_qualitativo": "reduz exposicao patrimonial em caso de morte",
        "ancora_metodologica": "cerbasi",
        "tema_canonico": "Proteção",
        "confianca": "alta",
        "section_id": "S9",
        "suggestion_dedup_key": "a" * 64,
        "impacto_estimado": {
            "valor_estimado_brl": 150000.0,
            "unidade": "ano",
            "caveat": "estimativa baseada em dados de mercado",
        },
    }


def make_artifact_content() -> dict:
    return {
        "version": "1.0",
        "metadata": {
            "persona_hash": PERSONA_HASH,
            "manifest_version": "1.0",
            "schema_version": "1.0",
            "model_id": "anthropic/claude-sonnet-4-20250514",
            "tier_at_generation": "premium",
            "generated_at": "2026-05-13T16:00:00+00:00",
        },
        "diagnostico_geral": "diagnostico minimo aceito pelo schema validator do output",
        "pontos_fortes": [],
        "riscos": [],
        "sugestoes_execucao": [_make_sugestao_with_impacto()],
        "sugestoes_taticas": [],
        "sugestoes_estrategicas": [],
        "metricas": [],
        "notas_metodologicas": [],
    }


async def make_artifacts(db, workspace, run):
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
        content_json=make_artifact_content(),
    )
    db.add(e5)
    db.add(parecer)
    await db.flush()
    return e5, parecer


def _assert_review_row(sync_session, workspace_id: str) -> None:
    rows = (
        sync_session.execute(
            select(PlannerReview).where(PlannerReview.workspace_id == workspace_id)
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].status == "Gerado"
    assert rows[0].cost_usd_cents == 42  # 0.42 USD → 42 cents
    assert rows[0].persona_hash == PERSONA_HASH


def _assert_suggestion_row(sync_session, workspace_id: str) -> None:
    rows = (
        sync_session.execute(select(Suggestion).where(Suggestion.workspace_id == workspace_id))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    s = rows[0]
    assert s.origin == "llm"
    assert s.kind == "parecer_planejador"
    assert s.severity == "danger"  # P0 → danger
    assert s.dedup_key == "a" * 64
    assert s.amount_brl_cents == 15_000_000  # 150_000.00 BRL → cents


@pytest.mark.asyncio
async def test_persist_creates_review_and_suggestion(db, sync_session):
    """Happy path — aggregate (com custo em review.cost_usd_cents) + suggestion
    criados em uma transação. DE-01 Fase 1: sem row em pipeline_run_costs."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    await make_artifacts(db, workspace, run)
    await db.commit()

    review_id = persist_planner_review(
        sync_session, workspace_id=workspace.id, run_id=run.id, detail=make_detail()
    )
    sync_session.commit()
    assert review_id is not None
    _assert_review_row(sync_session, workspace.id)
    _assert_suggestion_row(sync_session, workspace.id)


@pytest.mark.asyncio
async def test_persist_from_stage_run_reads_e5_do_base_run(db, sync_session):
    """Run ``from_stage`` (ADR-291) não tem E5 próprio — o E5 vive no base_run
    pinado. Sem o fallback, o parecer regenerado nunca publicava PlannerReview
    (incidente 2026-06-12, run 79ddd9d3)."""
    workspace = await factories.make_workspace(db)
    base_run = await factories.make_run(db, workspace=workspace)
    await make_artifacts(db, workspace, base_run)

    retry_run = await factories.make_run(db, workspace=workspace)
    retry_run.base_run_id = base_run.id
    parecer_novo = PipelineArtifact(
        workspace_id=workspace.id,
        pipeline_run_id=retry_run.id,
        stage="E6-parecer",
        artifact_key="parecer_planejador",
        content_json=make_artifact_content(),
    )
    db.add(parecer_novo)
    await db.commit()

    review_id = persist_planner_review(
        sync_session, workspace_id=workspace.id, run_id=retry_run.id, detail=make_detail()
    )
    sync_session.commit()
    assert review_id is not None
    review = sync_session.get(PlannerReview, review_id)
    assert review.pipeline_run_id == retry_run.id


def _call_persist(sync_session, workspace_id: str, run_id: str) -> str | None:
    out = persist_planner_review(
        sync_session, workspace_id=workspace_id, run_id=run_id, detail=make_detail()
    )
    sync_session.commit()
    return out


@pytest.mark.asyncio
async def test_persist_idempotent_returns_existing(db, sync_session):
    """Re-execução do stage no mesmo run = no-op (retorna existente)."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    await make_artifacts(db, workspace, run)
    await db.commit()
    first = _call_persist(sync_session, workspace.id, run.id)
    second = _call_persist(sync_session, workspace.id, run.id)
    assert first == second
    reviews = (
        sync_session.execute(
            select(PlannerReview).where(PlannerReview.workspace_id == workspace.id)
        )
        .scalars()
        .all()
    )
    assert len(reviews) == 1


def _seed_preexisting_suggestion(sync_session, workspace_id: str) -> None:
    """Insert Suggestion com dedup_key igual à que viria do parecer."""
    sync_session.add(
        Suggestion(
            workspace_id=workspace_id,
            section_id="S9",
            kind="parecer_planejador",
            origin="llm",
            severity="danger",
            title="existente",
            rationale="prévia",
            dedup_key="a" * 64,
            status="Pendente",
        )
    )
    sync_session.commit()


@pytest.mark.asyncio
async def test_persist_skips_existing_suggestion_dedup(db, sync_session):
    """Sugestão com mesmo dedup_key no workspace ⇒ não duplica (ADR-153)."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    await make_artifacts(db, workspace, run)
    await db.commit()
    _seed_preexisting_suggestion(sync_session, workspace.id)
    persist_planner_review(
        sync_session, workspace_id=workspace.id, run_id=run.id, detail=make_detail()
    )
    sync_session.commit()
    suggestions = (
        sync_session.execute(select(Suggestion).where(Suggestion.workspace_id == workspace.id))
        .scalars()
        .all()
    )
    assert len(suggestions) == 1  # Só a pré-existente (não duplicou)


@pytest.mark.asyncio
async def test_persist_handles_missing_artifacts_gracefully(db, sync_session):
    """Stage rodou sem deixar artifact = retorna None + log warning."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    await db.commit()

    result = persist_planner_review(
        sync_session, workspace_id=workspace.id, run_id=run.id, detail=make_detail()
    )
    assert result is None


@pytest.mark.asyncio
async def test_persist_after_stage_success_resolves_workspace(db, sync_session):
    """Entry point alto-nível só recebe run_id; resolve workspace via FK."""
    workspace = await factories.make_workspace(db)
    run = await factories.make_run(db, workspace=workspace)
    await make_artifacts(db, workspace, run)
    await db.commit()

    review_id = persist_after_stage_success(sync_session, run_id=run.id, detail=make_detail())
    assert review_id is not None
