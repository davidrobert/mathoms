"""Helpers compartilhados dos testes de ciclo de vida de Suggestion do parecer (ADR-290/ADR-376) — construção de artifact sintético, seed e leitura por status."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.suggestion import Suggestion
from backend.app.services.parecer_finalization import (
    compute_suggestion_dedup_key,
    compute_suggestion_thesis_key,
)
from backend.app.services.planner_review_persistence import persist_planner_review
from backend.tests import factories

PERSONA_HASH = "b" * 64

_SUG_BASE = {
    "prioridade": "P1",
    "impacto_qualitativo": "impacto sintetico para teste de supersede",
    "confianca": "media",
}


def make_detail(**overrides) -> dict:
    detail = {
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
    detail.update(overrides)
    return detail


def make_sugestao(
    *,
    workspace_id: str,
    acao: str,
    tema: Optional[str] = "Liquidez",
    section_id: str = "S3",
    ancora: str = "convergencia",
    impacto: Optional[str] = None,
) -> dict:
    dedup = compute_suggestion_dedup_key(workspace_id=workspace_id, ancora=ancora, acao=acao)
    optionals = {"impacto_qualitativo": impacto, "tema_canonico": tema}
    return {
        **_SUG_BASE,
        "acao": acao,
        "ancora_metodologica": ancora,
        "section_id": section_id,
        "suggestion_dedup_key": dedup,
        **{k: v for k, v in optionals.items() if v is not None},
    }


_ARTIFACT_METADATA = {
    "persona_hash": PERSONA_HASH,
    "manifest_version": "1.0",
    "schema_version": "1.0",
    "model_id": "anthropic/claude-sonnet-4-20250514",
    "tier_at_generation": "premium",
    "generated_at": "2026-06-12T16:00:00+00:00",
}


def make_content(
    sugestoes: list[dict],
    *,
    taticas: Optional[list[dict]] = None,
    estrategicas: Optional[list[dict]] = None,
) -> dict:
    return {
        "version": "1.0",
        "metadata": dict(_ARTIFACT_METADATA),
        "diagnostico_geral": "diagnostico minimo aceito pelo schema validator do output",
        "pontos_fortes": [],
        "riscos": [],
        "sugestoes_execucao": sugestoes,
        "sugestoes_taticas": taticas or [],
        "sugestoes_estrategicas": estrategicas or [],
        "metricas": [],
        "notas_metodologicas": [],
    }


def _bucket_sugestoes(workspace_id: str, acoes: Optional[list[dict]] = None) -> list[dict]:
    return [make_sugestao(workspace_id=workspace_id, **kw) for kw in acoes or []]


async def make_run_with_acoes(
    db,
    workspace,
    acoes: list[dict],
    *,
    taticas: Optional[list[dict]] = None,
    estrategicas: Optional[list[dict]] = None,
):
    """Run + artifacts E5/parecer; acoes = kwargs extras de make_sugestao por item."""
    content = make_content(
        _bucket_sugestoes(workspace.id, acoes),
        taticas=_bucket_sugestoes(workspace.id, taticas),
        estrategicas=_bucket_sugestoes(workspace.id, estrategicas),
    )
    run = await factories.make_run(db, workspace=workspace)
    await _add_run_artifacts(db, workspace, run, content)
    return run


async def _add_run_artifacts(db, workspace, run, parecer_content: dict) -> None:
    for stage, key, payload in (
        ("E5", "analise_financeira", {"narrativas": {}}),
        ("E6-parecer", "parecer_planejador", parecer_content),
    ):
        db.add(
            PipelineArtifact(
                workspace_id=workspace.id,
                pipeline_run_id=run.id,
                stage=stage,
                artifact_key=key,
                content_json=payload,
            )
        )
    await db.flush()


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


def persist_run(sync_session, workspace_id: str, run_id: str, **detail_overrides) -> None:
    persist_planner_review(
        sync_session,
        workspace_id=workspace_id,
        run_id=run_id,
        detail=make_detail(**detail_overrides),
    )
    sync_session.commit()


def all_suggestions(sync_session, workspace_id: str) -> list[Suggestion]:
    return list(
        sync_session.execute(select(Suggestion).where(Suggestion.workspace_id == workspace_id))
        .scalars()
        .all()
    )


def by_status(sync_session, workspace_id: str, status: str) -> list[Suggestion]:
    return [s for s in all_suggestions(sync_session, workspace_id) if s.status == status]


def default_thesis(workspace_id: str) -> str:
    return compute_suggestion_thesis_key(
        workspace_id=workspace_id, tema_canonico="Liquidez", section_id="S3", ancora="convergencia"
    )


def parecer_artifact_for_run(sync_session, run_id: str) -> PipelineArtifact:
    return sync_session.execute(
        select(PipelineArtifact).where(
            PipelineArtifact.pipeline_run_id == run_id,
            PipelineArtifact.artifact_key == "parecer_planejador",
        )
    ).scalar_one()


def expire_stats_for_run(sync_session, workspace_id: str, run_id: str) -> dict[str, int]:
    """Chama o service direto (sem o guard run-level do persist) e devolve os contadores KR4."""
    from backend.app.models.planner_review import ParecerOutcome
    from backend.app.services.suggestion_supersede import persist_suggestions_for_run

    stats = persist_suggestions_for_run(
        sync_session,
        workspace_id=workspace_id,
        run_id=run_id,
        parecer_artifact=parecer_artifact_for_run(sync_session, run_id),
        outcome=ParecerOutcome.entregue,
    )
    sync_session.commit()
    return stats
