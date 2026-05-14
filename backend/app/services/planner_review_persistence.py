"""Persistência atômica do PlannerReview pós-stage (ADR-199 / ADR-204 / ADR-208) — review + cost + suggestions(origin=llm) em transação única; falha → rollback + log."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun
from backend.app.models.pipeline_run_cost import PipelineRunCost
from backend.app.models.planner_field_request import PlannerFieldRequest
from backend.app.models.planner_review import PlannerReview
from backend.app.models.suggestion import Suggestion
from backend.app.services.parecer_finalization import severity_from_prioridade

logger = logging.getLogger("mathoms.pipeline.planner_review_persistence")

# Stage names + artifact keys — fonte de verdade local (espelha
# pipeline.stages.parecer_planejador).
_PARECER_STAGE = "E6-parecer"
_PARECER_KEY = "parecer_planejador"
_E5_STAGE = "E5"
_E5_KEY = "analise_financeira"
_SUGGESTION_KIND = "parecer_planejador"


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
                PipelineArtifact.stage == stage,
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
        items_shown_count=_sum_shown(parecer_artifact.content_json),
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


def _existing_dedup_keys(db: Session, *, workspace_id: str) -> set[str]:
    """Suggestions ativas (qualquer status) para o workspace — idempotência ADR-153."""
    rows = db.execute(
        select(Suggestion.dedup_key).where(Suggestion.workspace_id == workspace_id)
    ).all()
    return {row[0] for row in rows}


def _iter_sugestoes(content_json: dict):
    """Yields tuples (horizon, sug_dict) achatando os 3 buckets."""
    for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
        for sug in content_json.get(horizon, []) or []:
            yield horizon, sug


def _build_suggestion(*, workspace_id: str, report_id: Optional[str], sug: dict) -> Suggestion:
    """Constrói Suggestion(origin='llm') — title vem do `acao`, rationale do `impacto`."""
    return Suggestion(
        workspace_id=workspace_id,
        report_id=report_id,
        section_id=sug["section_id"],
        kind=_SUGGESTION_KIND,
        category=None,
        origin="llm",
        severity=severity_from_prioridade(sug["prioridade"]),
        title=sug["acao"][:500],
        rationale=sug["impacto_qualitativo"],
        amount_brl_cents=_extract_amount_cents(sug),
        dedup_key=sug["suggestion_dedup_key"],
        status="Pendente",
    )


def _extract_amount_cents(sug: dict) -> Optional[int]:
    """Converte ``impacto_estimado.valor_estimado_brl`` (BRL) → cents (ADR-090). Opcional — só presente quando confianca='alta' (ADR-202 §D6)."""
    impacto = sug.get("impacto_estimado")
    if not impacto:
        return None
    valor_brl = impacto.get("valor_estimado_brl")
    if valor_brl is None:
        return None
    return int(round(float(valor_brl) * 100))


def _find_report_id(db: Session, *, workspace_id: str, run_id: str) -> Optional[str]:
    """Resolve `report_id` para FK opcional em Suggestion. None = ainda sem Report."""
    from backend.app.models.report import Report

    row = (
        db.execute(
            select(Report.id).where(
                Report.workspace_id == workspace_id,
                Report.pipeline_run_id == run_id,
            )
        )
        .scalars()
        .first()
    )
    return row


def _load_artifacts(
    db: Session, *, workspace_id: str, run_id: str
) -> Optional[tuple[PipelineArtifact, PipelineArtifact]]:
    """Carrega (parecer, E5) artifacts; ``None`` se algum sumiu."""
    kwargs = {"workspace_id": workspace_id, "run_id": run_id}
    parecer = _find_artifact(db, stage=_PARECER_STAGE, key=_PARECER_KEY, **kwargs)
    e5 = _find_artifact(db, stage=_E5_STAGE, key=_E5_KEY, **kwargs)
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


def _persist_suggestions_from_artifact(
    db: Session, *, workspace_id: str, parecer_artifact: PipelineArtifact
) -> int:
    """Bulk-insert de Suggestions com dedup; retorna count criado."""
    existing_keys = _existing_dedup_keys(db, workspace_id=workspace_id)
    report_id = _find_report_id(
        db, workspace_id=workspace_id, run_id=parecer_artifact.pipeline_run_id
    )
    created = 0
    for _horizon, sug in _iter_sugestoes(parecer_artifact.content_json):
        if sug["suggestion_dedup_key"] in existing_keys:
            continue
        db.add(_build_suggestion(workspace_id=workspace_id, report_id=report_id, sug=sug))
        existing_keys.add(sug["suggestion_dedup_key"])
        created += 1
    return created


def _iter_field_requests(content_json: dict):
    """Yields dicts ``{field_path, motivo}`` do array ``campos_faltantes_pediria_se_iterasse``."""
    campos = content_json.get("campos_faltantes_pediria_se_iterasse")
    if not campos:
        return
    for entry in campos:
        if not isinstance(entry, dict):
            continue
        path = entry.get("field_path")
        motivo = entry.get("motivo")
        if not path or not motivo:
            continue
        yield {"field_path": path, "motivo": motivo}


def _build_field_request(*, workspace_id: str, review_id: str, entry: dict) -> PlannerFieldRequest:
    """Constrói row de telemetria do parecer (ADR-206 §D2 fonte primária)."""
    return PlannerFieldRequest(
        workspace_id=workspace_id,
        planner_review_id=review_id,
        field_path=entry["field_path"],
        motivo=entry["motivo"],
        reason="llm_declared",
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
    for entry in _iter_field_requests(parecer_artifact.content_json):
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
    created = _persist_suggestions_from_artifact(
        db, workspace_id=workspace_id, parecer_artifact=parecer_artifact
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
            "suggestions_created": created,
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
        return review_id
    except Exception:  # noqa: BLE001 — log e segue; artifact já está commitado
        db.rollback()
        logger.exception("planner_review_persistence_failed", extra={"run_id": run_id})
        return None


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
