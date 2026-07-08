"""Persistência atômica do PlannerReview pós-stage (ADR-199 / ADR-204 / ADR-208) — review + cost + suggestions(origin=llm) em transação única; falha → rollback + log."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun
from backend.app.models.pipeline_run_cost import PipelineRunCost
from backend.app.models.planner_field_request import (
    VALID_FIELD_REQUEST_REASONS,
    PlannerFieldRequest,
)
from backend.app.models.planner_review import PlannerReview
from backend.app.services.security.crypto import read_artifact_content
from backend.app.services.suggestion_supersede import persist_suggestions_for_run
from pipeline.artifact_store import stage_aliases

logger = logging.getLogger("mathoms.pipeline.planner_review_persistence")

# Stage names + artifact keys — fonte de verdade local (espelha
# pipeline.stages.parecer_planejador).
_PARECER_STAGE = "review_finances_holistic"
_PARECER_KEY = "parecer_planejador"
_E5_STAGE = "analyze_finances"
_E5_KEY = "analise_financeira"


def _usd_to_cents(usd: float) -> int:
    """USD float → cents int (ADR-090 — money em cents)."""
    return int(round(usd * 100))


def _find_artifact(
    db: Session, *, workspace_id: str, run_id: str, stage: str, key: str
) -> Optional[PipelineArtifact]:
    """Localiza artifact por (ws, run, stage, key) — fonte canônica da geração."""
    row = (
        db.execute(
            select(PipelineArtifact).where(
                PipelineArtifact.workspace_id == workspace_id,
                PipelineArtifact.pipeline_run_id == run_id,
                PipelineArtifact.stage.in_(stage_aliases(stage)),
                PipelineArtifact.artifact_key == key,
            )
        )
        .scalars()
        .first()
    )
    return row


def _review_audit_fields(detail: dict) -> dict:
    """Campos de auditoria extraídos do detail (persona, manifest, model, tier)."""
    return {
        "persona_hash": detail["persona_hash"],
        "manifest_version": detail["manifest_version"],
        "schema_version": detail["schema_version"],
        "model_id": detail["model_id"],
        "tier_at_generation": detail["tier_at_generation"],
    }


def _review_metrics_fields(detail: dict) -> dict:
    """Campos de métrica do detail (tokens, cost, latency, iterations)."""
    tokens = detail.get("tokens", {})
    return {
        "cost_usd_cents": _usd_to_cents(detail.get("cost_usd", 0.0)),
        "tokens_in": tokens.get("in", 0),
        "tokens_out": tokens.get("out", 0),
        "tool_iterations": detail.get("tool_iterations", 0),
        "latency_ms": detail.get("latency_ms", 0),
    }


def _build_review(
    *,
    workspace_id: str,
    run_id: str,
    parecer_artifact: PipelineArtifact,
    e5_artifact: PipelineArtifact,
    detail: dict,
) -> PlannerReview:
    """Empacota PlannerReview a partir do detail do stage + IDs de artifact."""
    return PlannerReview(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        pipeline_artifact_id=parecer_artifact.id,
        e5_artifact_id=e5_artifact.id,
        status="Gerado",  # ADR-204 §D1
        items_shown_count=_sum_shown(read_artifact_content(parecer_artifact.content_json) or {}),
        items_gated_count=0,
        **_review_audit_fields(detail),
        **_review_metrics_fields(detail),
    )


def _sum_shown(content_json: dict) -> int:
    """Soma dos buckets gerados (premium baseline)."""
    return sum(
        len(content_json.get(k, []))
        for k in (
            "pontos_fortes",
            "riscos",
            "sugestoes_execucao",
            "sugestoes_taticas",
            "sugestoes_estrategicas",
            "metricas",
            "notas_metodologicas",
        )
    )


def _build_cost_row(*, workspace_id: str, run_id: str, detail: dict) -> PipelineRunCost:
    return PipelineRunCost(
        pipeline_run_id=run_id,
        workspace_id=workspace_id,
        stage="review_finances_holistic",
        model_id=detail["model_id"],
        tokens_in=detail.get("tokens", {}).get("in", 0),
        tokens_out=detail.get("tokens", {}).get("out", 0),
        cost_usd_cents=_usd_to_cents(detail.get("cost_usd", 0.0)),
        latency_ms=detail.get("latency_ms", 0),
        tool_iterations=detail.get("tool_iterations"),
    )


def _find_e5_with_base_run_fallback(
    db: Session, *, workspace_id: str, run_id: str
) -> Optional[PipelineArtifact]:
    """E5 do run; em run ``from_stage`` (ADR-291) o E5 vive no base_run pinado."""
    e5 = _find_artifact(db, workspace_id=workspace_id, run_id=run_id, stage=_E5_STAGE, key=_E5_KEY)
    if e5 is not None:
        return e5
    run = db.get(PipelineRun, run_id)
    base_run_id = run.base_run_id if run is not None else None
    if not base_run_id:
        return None
    return _find_artifact(
        db, workspace_id=workspace_id, run_id=base_run_id, stage=_E5_STAGE, key=_E5_KEY
    )


def _load_artifacts(
    db: Session, *, workspace_id: str, run_id: str
) -> Optional[tuple[PipelineArtifact, PipelineArtifact]]:
    """Carrega (parecer, E5) artifacts; ``None`` se algum sumiu."""
    kwargs = {"workspace_id": workspace_id, "run_id": run_id}
    parecer = _find_artifact(db, stage=_PARECER_STAGE, key=_PARECER_KEY, **kwargs)
    e5 = _find_e5_with_base_run_fallback(db, **kwargs)
    if parecer is None or e5 is None:
        logger.warning(
            "planner_review_persistence_artifacts_missing",
            extra={**kwargs, "has_parecer": parecer is not None, "has_e5": e5 is not None},
        )
        return None
    return parecer, e5


def _find_existing_review(
    db: Session, *, workspace_id: str, run_id: str
) -> Optional[PlannerReview]:
    """Retorna PlannerReview existente para o run (idempotência)."""
    return (
        db.execute(
            select(PlannerReview).where(
                PlannerReview.workspace_id == workspace_id,
                PlannerReview.pipeline_run_id == run_id,
            )
        )
        .scalars()
        .first()
    )


def _field_request_entry(entry, default_reason: str) -> Optional[dict]:
    """Normaliza entrada crua em ``{field_path, motivo, reason}``; inválida → None."""
    if not isinstance(entry, dict):
        return None
    path, motivo = entry.get("field_path"), entry.get("motivo")
    if not path or not motivo:
        return None
    reason = entry.get("reason")
    if reason not in VALID_FIELD_REQUEST_REASONS:
        reason = default_reason
    return {"field_path": path, "motivo": motivo, "reason": reason}


def _iter_field_requests(content_json: dict):
    """Yields ``{field_path, motivo, reason}`` — array ``campos_faltantes_pediria_se_
    iterasse`` (mantidos pelo filtro 3-vias → llm_declared) + ``_meta.field_request_
    audit`` (removidos — spurious/wrong_path, A28.l11)."""
    for entry in content_json.get("campos_faltantes_pediria_se_iterasse") or []:
        row = _field_request_entry(entry, "llm_declared")
        if row:
            yield row
    audit = (content_json.get("_meta") or {}).get("field_request_audit") or []
    for entry in audit:
        row = _field_request_entry(entry, "llm_declared")
        if row:
            yield row


def _build_field_request(*, workspace_id: str, review_id: str, entry: dict) -> PlannerFieldRequest:
    """Constrói row de telemetria do parecer (ADR-206 §D2 fonte primária + A28.l11)."""
    return PlannerFieldRequest(
        workspace_id=workspace_id,
        planner_review_id=review_id,
        field_path=entry["field_path"],
        motivo=entry["motivo"],
        reason=entry.get("reason", "llm_declared"),
    )


def _persist_field_requests(
    db: Session,
    *,
    workspace_id: str,
    review_id: str,
    parecer_artifact: PipelineArtifact,
) -> int:
    """Bulk-insert. Idempotente via UNIQUE (review_id, field_path); dedup intra-batch defensivo."""
    seen: set[str] = set()
    created = 0
    for entry in _iter_field_requests(read_artifact_content(parecer_artifact.content_json) or {}):
        path = entry["field_path"]
        if path in seen:
            continue
        seen.add(path)
        db.add(_build_field_request(workspace_id=workspace_id, review_id=review_id, entry=entry))
        created += 1
    return created


def _do_persist(
    db: Session,
    *,
    workspace_id: str,
    run_id: str,
    parecer_artifact: PipelineArtifact,
    e5_artifact: PipelineArtifact,
    detail: dict,
) -> str:
    """Insere review + cost + suggestions + field_requests (assume idempotência já verificada)."""
    review = _build_review(
        workspace_id=workspace_id,
        run_id=run_id,
        parecer_artifact=parecer_artifact,
        e5_artifact=e5_artifact,
        detail=detail,
    )
    cost_row = _build_cost_row(workspace_id=workspace_id, run_id=run_id, detail=detail)
    db.add(review)
    db.add(cost_row)
    # Flush para garantir ``review.id`` disponível antes de FKs em field_requests.
    db.flush()
    suggestion_stats = persist_suggestions_for_run(
        db, workspace_id=workspace_id, run_id=run_id, parecer_artifact=parecer_artifact
    )
    field_requests_created = _persist_field_requests(
        db,
        workspace_id=workspace_id,
        review_id=review.id,
        parecer_artifact=parecer_artifact,
    )
    logger.info(
        "planner_review_persistence_committed",
        extra={
            "workspace_id": workspace_id,
            "run_id": run_id,
            "review_id": review.id,
            **suggestion_stats,
            "field_requests_created": field_requests_created,
            "cost_usd_cents": cost_row.cost_usd_cents,
        },
    )
    return review.id


def persist_planner_review(
    db: Session, *, workspace_id: str, run_id: str, detail: dict
) -> Optional[str]:
    """Persiste aggregate + cost + suggestions. Idempotente por (ws, run_id)."""
    artifacts = _load_artifacts(db, workspace_id=workspace_id, run_id=run_id)
    if artifacts is None:
        return None
    existing = _find_existing_review(db, workspace_id=workspace_id, run_id=run_id)
    if existing is not None:
        logger.info(
            "planner_review_persistence_idempotent",
            extra={"workspace_id": workspace_id, "run_id": run_id, "review_id": existing.id},
        )
        return existing.id
    parecer_artifact, e5_artifact = artifacts
    return _do_persist(
        db,
        workspace_id=workspace_id,
        run_id=run_id,
        parecer_artifact=parecer_artifact,
        e5_artifact=e5_artifact,
        detail=detail,
    )


def _workspace_id_from_run(db: Session, run_id: str) -> Optional[str]:
    """Resolve workspace_id a partir do run_id — usado no caller (pipeline_task)."""
    row = db.execute(
        select(PipelineRun.workspace_id).where(PipelineRun.id == run_id)
    ).scalar_one_or_none()
    return row


def _safe_persist(db: Session, *, workspace_id: str, run_id: str, detail: dict) -> Optional[str]:
    """Wrap persist_planner_review com rollback/log em exceção (não propaga)."""
    try:
        review_id = persist_planner_review(
            db, workspace_id=workspace_id, run_id=run_id, detail=detail
        )
        db.commit()
    except Exception:  # noqa: BLE001 — log e segue; artifact já está commitado
        db.rollback()
        logger.exception("planner_review_persistence_failed", extra={"run_id": run_id})
        return None
    # A22.l4 — drift observability pós-commit; fail-open próprio (não desfaz o review).
    from backend.app.services.parecer_drift_monitor import emit_parecer_drift

    emit_parecer_drift(db, workspace_id)
    return review_id


def persist_after_stage_success(db: Session, *, run_id: str, detail: dict) -> Optional[str]:
    """Entry point do ``_record_stage_result`` — resolve workspace + delega."""
    workspace_id = _workspace_id_from_run(db, run_id)
    if not workspace_id:
        logger.warning("planner_review_persistence_run_missing", extra={"run_id": run_id})
        return None
    return _safe_persist(db, workspace_id=workspace_id, run_id=run_id, detail=detail)


__all__ = [
    "persist_after_stage_success",
    "persist_planner_review",
]
