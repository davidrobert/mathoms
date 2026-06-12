"""Supersede-per-run + thesis_key para Suggestion origin='llm' (ADR-290 B1–B6) — aceite F1 do PLAN-suggestion-lifecycle: run novo supersede teses obsoletas; retry do mesmo run não supersede; aceitas/deterministic/thesis NULL intocadas; janela de dismiss não recria."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Generator, Optional

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.suggestion import Suggestion
from backend.app.services.parecer_finalization import (
    compute_suggestion_dedup_key,
    compute_suggestion_thesis_key,
)
from backend.app.services.planner_review_persistence import persist_planner_review
from backend.tests import factories

PERSONA_HASH = "b" * 64


@pytest.fixture
def sync_session() -> Generator[Session, None, None]:
    s = SyncSessionLocal()
    try:
        yield s
    finally:
        s.close()


def make_detail() -> dict:
    return {
        "success": True,
        "status": "Gerado",
        "cache_hit": False,
        "tokens": {"in": 5000, "out": 1000},
        "cost_usd": 0.10,
        "latency_ms": 5000,
        "tool_iterations": 1,
        "model_id": "anthropic/claude-sonnet-4-20250514",
        "persona_hash": PERSONA_HASH,
        "manifest_version": "1.0",
        "schema_version": "1.0",
        "tier_at_generation": "premium",
    }


_SUG_BASE = {
    "prioridade": "P1",
    "impacto_qualitativo": "impacto sintetico para teste de supersede",
    "confianca": "media",
}


def make_sugestao(
    *,
    workspace_id: str,
    acao: str,
    tema: Optional[str] = "Liquidez",
    section_id: str = "S3",
    ancora: str = "convergencia",
) -> dict:
    dedup = compute_suggestion_dedup_key(workspace_id=workspace_id, ancora=ancora, acao=acao)
    sug = {
        **_SUG_BASE,
        "acao": acao,
        "ancora_metodologica": ancora,
        "section_id": section_id,
        "suggestion_dedup_key": dedup,
    }
    if tema is not None:
        sug["tema_canonico"] = tema
    return sug


def make_content(sugestoes: list[dict]) -> dict:
    return {
        "version": "1.0",
        "metadata": {
            "persona_hash": PERSONA_HASH,
            "manifest_version": "1.0",
            "schema_version": "1.0",
            "model_id": "anthropic/claude-sonnet-4-20250514",
            "tier_at_generation": "premium",
            "generated_at": "2026-06-12T16:00:00+00:00",
        },
        "diagnostico_geral": "diagnostico minimo aceito pelo schema validator do output",
        "pontos_fortes": [],
        "riscos": [],
        "sugestoes_execucao": sugestoes,
        "sugestoes_taticas": [],
        "sugestoes_estrategicas": [],
        "metricas": [],
        "notas_metodologicas": [],
    }


async def make_run_with_acoes(db, workspace, acoes: list[dict]):
    """Run + artifacts E5/parecer; acoes = kwargs extras de make_sugestao por item."""
    sugestoes = [make_sugestao(workspace_id=workspace.id, **kw) for kw in acoes]
    run = await factories.make_run(db, workspace=workspace)
    for stage, key, content in (
        ("E5", "analise_financeira", {"narrativas": {}}),
        ("E6-parecer", "parecer_planejador", make_content(sugestoes)),
    ):
        db.add(
            PipelineArtifact(
                workspace_id=workspace.id,
                pipeline_run_id=run.id,
                stage=stage,
                artifact_key=key,
                content_json=content,
            )
        )
    await db.flush()
    return run


def seed_suggestion(sync_session, workspace_id: str, **overrides) -> None:
    defaults = {
        "workspace_id": workspace_id,
        "section_id": "S3",
        "kind": "parecer_planejador",
        "origin": "llm",
        "severity": "warning",
        "title": "seed",
        "rationale": "r",
        "dedup_key": "0" * 64,
        "status": "Pendente",
    }
    sync_session.add(Suggestion(**{**defaults, **overrides}))
    sync_session.commit()


def _persist(sync_session, workspace_id: str, run_id: str) -> None:
    persist_planner_review(
        sync_session, workspace_id=workspace_id, run_id=run_id, detail=make_detail()
    )
    sync_session.commit()


def _all_suggestions(sync_session, workspace_id: str) -> list[Suggestion]:
    return list(
        sync_session.execute(select(Suggestion).where(Suggestion.workspace_id == workspace_id))
        .scalars()
        .all()
    )


def _by_status(sync_session, workspace_id: str, status: str) -> list[Suggestion]:
    return [s for s in _all_suggestions(sync_session, workspace_id) if s.status == status]


@pytest.mark.asyncio
async def test_second_run_supersedes_obsolete_thesis(db, sync_session):
    """Tese que não reaparece no run novo vira Superseded; count(Pendente) não cresce."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    run2 = await make_run_with_acoes(
        db, workspace, [{"acao": "rever alocacao em renda fixa", "tema": "Alocação"}]
    )
    await db.commit()
    _persist(sync_session, workspace.id, run1.id)
    _persist(sync_session, workspace.id, run2.id)

    pendentes = _by_status(sync_session, workspace.id, "Pendente")
    superseded = _by_status(sync_session, workspace.id, "Superseded")
    assert [s.title for s in pendentes] == ["rever alocacao em renda fixa"]
    assert [s.title for s in superseded] == ["aumentar reserva"]
    assert superseded[0].superseded_by_run_id == run2.id
    assert superseded[0].superseded_at is not None


@pytest.mark.asyncio
async def test_same_run_retry_does_not_supersede(db, sync_session):
    """2ª chamada para o MESMO run é no-op (guard run-level, B6)."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    await db.commit()
    _persist(sync_session, workspace.id, run1.id)
    _persist(sync_session, workspace.id, run1.id)

    assert len(_by_status(sync_session, workspace.id, "Pendente")) == 1
    assert len(_by_status(sync_session, workspace.id, "Superseded")) == 0


@pytest.mark.asyncio
async def test_reappearing_thesis_same_wording_kept(db, sync_session):
    """Mesma tese + mesma redação no run novo → linha original sobrevive Pendente."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    await db.commit()
    _persist(sync_session, workspace.id, run1.id)
    _persist(sync_session, workspace.id, run2.id)

    rows = _all_suggestions(sync_session, workspace.id)
    assert len(rows) == 1
    assert rows[0].status == "Pendente"


@pytest.mark.asyncio
async def test_reworded_thesis_supersedes_old_and_inserts_new(db, sync_session):
    """Mesma tese re-redigida (dedup novo) → antiga Superseded, nova Pendente (KR1)."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva para seis meses"}])
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "elevar a reserva de emergencia"}])
    await db.commit()
    _persist(sync_session, workspace.id, run1.id)
    _persist(sync_session, workspace.id, run2.id)

    pendentes = _by_status(sync_session, workspace.id, "Pendente")
    superseded = _by_status(sync_session, workspace.id, "Superseded")
    assert [s.title for s in pendentes] == ["elevar a reserva de emergencia"]
    assert len(superseded) == 1
    assert pendentes[0].thesis_key == superseded[0].thesis_key


@pytest.mark.asyncio
async def test_accepted_suggestion_never_superseded(db, sync_session):
    """Aceita (histórico sagrado, B3) nunca entra no conjunto superseable."""
    workspace = await factories.make_workspace(db)
    run2 = await make_run_with_acoes(
        db, workspace, [{"acao": "rever alocacao", "tema": "Alocação"}]
    )
    await db.commit()
    seed_suggestion(
        sync_session,
        workspace.id,
        title="aceita historica",
        dedup_key="c" * 64,
        thesis_key="d" * 64,
        status="Aceita",
    )
    _persist(sync_session, workspace.id, run2.id)

    aceitas = _by_status(sync_session, workspace.id, "Aceita")
    assert len(aceitas) == 1
    assert aceitas[0].superseded_at is None


@pytest.mark.asyncio
async def test_deterministic_origin_untouched(db, sync_session):
    """origin='deterministic' tem ciclo de vida próprio (B5) — intocado."""
    workspace = await factories.make_workspace(db)
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "rever alocacao"}])
    await db.commit()
    seed_suggestion(
        sync_session,
        workspace.id,
        title="deterministica",
        kind="reserva_insuficiente",
        origin="deterministic",
        dedup_key="e" * 64,
        thesis_key="f" * 64,
    )
    _persist(sync_session, workspace.id, run2.id)

    rows = {s.title: s.status for s in _all_suggestions(sync_session, workspace.id)}
    assert rows["deterministica"] == "Pendente"


@pytest.mark.asyncio
async def test_null_thesis_key_untouched(db, sync_session):
    """Linha pré-F1 (thesis_key NULL) fica fora do supersede — fallback seguro (B1)."""
    workspace = await factories.make_workspace(db)
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "rever alocacao"}])
    await db.commit()
    seed_suggestion(
        sync_session, workspace.id, title="legada sem thesis", dedup_key="1" * 64, thesis_key=None
    )
    _persist(sync_session, workspace.id, run2.id)

    rows = {s.title: s.status for s in _all_suggestions(sync_session, workspace.id)}
    assert rows["legada sem thesis"] == "Pendente"


def _default_thesis(workspace_id: str) -> str:
    return compute_suggestion_thesis_key(
        workspace_id=workspace_id, tema_canonico="Liquidez", section_id="S3", ancora="convergencia"
    )


@pytest.mark.asyncio
async def test_dismissed_thesis_within_window_not_recreated(db, sync_session):
    """Descartada <90d com mesma tese bloqueia recriação re-redigida (B4)."""
    workspace = await factories.make_workspace(db)
    run2 = await make_run_with_acoes(db, workspace, [{"acao": "elevar reserva com nova redacao"}])
    await db.commit()
    thesis = _default_thesis(workspace.id)
    seed_suggestion(
        sync_session,
        workspace.id,
        title="descartada recente",
        dedup_key="2" * 64,
        thesis_key=thesis,
        status="Descartada",
        dismissed_reason="nao_se_aplica",
        dismissed_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    _persist(sync_session, workspace.id, run2.id)

    assert len(_by_status(sync_session, workspace.id, "Pendente")) == 0


@pytest.mark.asyncio
async def test_thesis_key_persisted_on_insert(db, sync_session):
    """B1 — thesis_key gravado na escrita = sha256(ws|tema|section|ancora)."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva"}])
    await db.commit()
    _persist(sync_session, workspace.id, run1.id)

    rows = _all_suggestions(sync_session, workspace.id)
    assert rows[0].thesis_key == compute_suggestion_thesis_key(
        workspace_id=workspace.id, tema_canonico="Liquidez", section_id="S3", ancora="convergencia"
    )


@pytest.mark.asyncio
async def test_thesis_key_null_when_source_field_missing(db, sync_session):
    """Artifact sem tema_canonico → thesis_key=None (fallback seguro, B1)."""
    workspace = await factories.make_workspace(db)
    run1 = await make_run_with_acoes(db, workspace, [{"acao": "aumentar reserva", "tema": None}])
    await db.commit()
    _persist(sync_session, workspace.id, run1.id)

    rows = _all_suggestions(sync_session, workspace.id)
    assert len(rows) == 1
    assert rows[0].thesis_key is None
