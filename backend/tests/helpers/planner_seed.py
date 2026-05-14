"""Helpers compartilhados para seed de ``PlannerReview`` em tests (ADR-199 Ato 6). Evita duplicação entre test_planner_field_requests/test_check_orphan/test_planner_telemetry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_review import PlannerReview

DEFAULT_PERSONA_HASH = "f" * 64


def build_e5_artifact(
    workspace_id: str, run_id: str, *, age_hours: Optional[int] = None
) -> PipelineArtifact:
    """Constrói ``PipelineArtifact`` para E5/analise_financeira (placeholder body)."""
    kwargs: dict = dict(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        stage="E5",
        artifact_key="analise_financeira",
        content_json={},
    )
    if age_hours is not None:
        kwargs["created_at"] = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    return PipelineArtifact(**kwargs)


def build_parecer_artifact(
    workspace_id: str,
    run_id: str,
    *,
    content_json: dict,
    age_hours: Optional[int] = None,
) -> PipelineArtifact:
    """Constrói ``PipelineArtifact`` para E6-parecer/parecer_planejador."""
    kwargs: dict = dict(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        stage="E6-parecer",
        artifact_key="parecer_planejador",
        content_json=content_json,
    )
    if age_hours is not None:
        kwargs["created_at"] = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    return PipelineArtifact(**kwargs)


_REVIEW_DEFAULTS: dict = {
    "status": "Gerado",
    "manifest_version": "1.0",
    "schema_version": "1.0",
    "model_id": "test",
    "tier_at_generation": "premium",
    "items_shown_count": 0,
    "items_gated_count": 0,
    "cost_usd_cents": 42,
    "tokens_in": 0,
    "tokens_out": 0,
    "tool_iterations": 0,
    "latency_ms": 0,
}


def build_planner_review(
    workspace_id: str,
    run_id: str,
    *,
    parecer_artifact_id: int,
    e5_artifact_id: int,
    persona_hash: str = DEFAULT_PERSONA_HASH,
) -> PlannerReview:
    """Constrói ``PlannerReview`` premium minimal — caller faz add+flush+commit."""
    return PlannerReview(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        pipeline_artifact_id=parecer_artifact_id,
        e5_artifact_id=e5_artifact_id,
        persona_hash=persona_hash,
        **_REVIEW_DEFAULTS,
    )


__all__ = [
    "DEFAULT_PERSONA_HASH",
    "build_e5_artifact",
    "build_parecer_artifact",
    "build_planner_review",
]
