"""Planner review API — Ato 5 (ADR-199 / ADR-208). GET retorna parecer com tier filter; POST /publish é idempotente (Gerado → Publicado, ADR-204)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.planner_review import (
    VALID_PLANNER_REVIEW_STATUSES,
    ParecerOutcome,
    PlannerReview,
)
from backend.app.models.report import Report
from backend.app.models.workspace import Workspace
from backend.app.repositories.planner_review_repository import (
    PlannerReviewRepository,
)
from backend.app.schemas.dto.planner_review import (
    PlannerReviewAbsence,
    PlannerReviewResponse,
    RetentionDetail,
)
from backend.app.services.audit import AuditAction
from backend.app.services.pipeline.pipeline_service import resolve_llm_tier_async
from backend.app.services.planner_review_tier_filter import apply_tier_filter
from backend.app.services.security.access_audit import record_access_audit
from backend.app.services.security.crypto import read_artifact_content

logger = logging.getLogger("mathoms.api.planner_review")

router = APIRouter(
    prefix="/workspaces/{workspace_id}/reports/{report_id}/planner-review",
    tags=["planner-review"],
)


_ABSENCE_MESSAGES = {
    "not_generated_yet": "Parecer ainda não gerado para este relatório.",
    "generation_unavailable": "Não foi possível gerar o parecer neste processamento.",
}

_PARECER_STAGE = "review_finances_holistic"
_PARECER_KEY = "parecer_planejador"

_ABSENCE_RESPONSES = {
    404: {
        "model": PlannerReviewAbsence,
        "description": "Sem parecer a servir — `code` diz por quê (ADR-366 §D6).",
    }
}


def _absent(code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": code, "message": _ABSENCE_MESSAGES[code]},
    )


# Quem discrimina é o SERVIDOR (ADR-366 §D6). A fonte é o artifact, não
# `stage_logs`: `_needs_review_return` grava o artifact ANTES de devolver
# `success: False` — inclusive nos 2 ramos de indisponibilidade —, e ele
# sobrevive à degradação (`commit_artifacts_on_degrade`, ADR-357 §6).
# Pós-A40.l20 PR2 o retido COM motivo tem row, então "sem row + com artifact"
# isola exatamente "o run tentou e não há o que servir".
async def _absence_code(db: AsyncSession, *, workspace_id: str, run_id: str) -> str:
    """`generation_unavailable` se o run tentou; `not_generated_yet` se nem rodou."""
    from sqlalchemy import select

    from pipeline.artifact_store import stage_aliases

    row = await db.execute(
        select(PipelineArtifact.id).where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.pipeline_run_id == run_id,
            PipelineArtifact.stage.in_(stage_aliases(_PARECER_STAGE)),
            PipelineArtifact.artifact_key == _PARECER_KEY,
        )
    )
    tentou = row.scalar_one_or_none() is not None
    return "generation_unavailable" if tentou else "not_generated_yet"


async def _resolve_run_id(db: AsyncSession, *, workspace_id: str, report_id: str) -> str:
    """Traduz report_id → pipeline_run_id; 404 quando relatório não existe."""
    from sqlalchemy import select

    row = await db.execute(
        select(Report.pipeline_run_id).where(
            Report.workspace_id == workspace_id,
            Report.id == report_id,
        )
    )
    run_id = row.scalar_one_or_none()
    if not run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "report_not_found", "message": "Relatório não encontrado."},
        )
    return run_id


async def _load_artifact(db: AsyncSession, artifact_id: int) -> dict:
    """Carrega `content_json` do artifact via FK; 404 se sumiu."""
    from sqlalchemy import select

    row = await db.execute(
        select(PipelineArtifact.content_json).where(PipelineArtifact.id == artifact_id)
    )
    content = row.scalar_one_or_none()
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "parecer_artifact_missing",
                "message": "Artifact do parecer não encontrado — possível inconsistência.",
            },
        )
    return read_artifact_content(content)


def _count_visible(content) -> int:
    """Soma dos buckets exibidos (pós-tier filter)."""
    return (
        len(content.pontos_fortes)
        + len(content.riscos)
        + len(content.sugestoes_execucao)
        + len(content.sugestoes_taticas)
        + len(content.sugestoes_estrategicas)
        + len(content.metricas)
        + len(content.notas_metodologicas)
    )


def _review_audit_dump(review: PlannerReview) -> dict:
    """Campos auditoria do review para DTO."""
    return {
        "id": review.id,
        "workspace_id": review.workspace_id,
        "pipeline_run_id": review.pipeline_run_id,
        "status": review.status,
        "persona_hash": review.persona_hash,
        "manifest_version": review.manifest_version,
        "schema_version": review.schema_version,
        "model_id": review.model_id,
        "tier_at_generation": review.tier_at_generation,
        "cost_usd_cents": review.cost_usd_cents,
        "created_at": review.created_at,
        "published_at": review.published_at,
        "superseded_at": review.superseded_at,
        "supersedes_id": review.supersedes_id,
        "superseded_by_id": review.superseded_by_id,
        "immutable_hash": review.immutable_hash,
    }


def _build_response(
    review: PlannerReview, content, items_gated_count_filtered: int
) -> PlannerReviewResponse:
    """Empacota DTO final — items_shown/gated refletem tier atual do request."""
    return PlannerReviewResponse(
        **_review_audit_dump(review),
        items_shown_count=_count_visible(content) if content is not None else 0,
        items_gated_count=items_gated_count_filtered,
        outcome=review.outcome,  # type: ignore[arg-type]
        retention=_retention_detail(review),
        content=content,
    )


@router.get(
    "",
    response_model=PlannerReviewResponse,
    responses=_ABSENCE_RESPONSES,
    dependencies=[
        Depends(
            record_access_audit(
                AuditAction.report_read, "planner_review", resource_id_param="report_id"
            )
        )
    ],
)
async def get_planner_review(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> PlannerReviewResponse:
    """Retorna parecer com tier filter aplicado (ADR-199 + ADR-208)."""
    run_id = await _resolve_run_id(db, workspace_id=workspace.id, report_id=report_id)
    repo = PlannerReviewRepository(db)
    review = await repo.get_latest_for_run(workspace.id, run_id)
    if review is None:
        raise _absent(await _absence_code(db, workspace_id=workspace.id, run_id=run_id))
    return await _render_review(db, workspace_id=workspace.id, review=review)


def _compute_immutable_hash(artifact: dict) -> str:
    """SHA-256 do content_json canônico (sorted keys) — ADR-204 §D2."""
    raw = json.dumps(artifact, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _retention_detail(review: PlannerReview) -> Optional[RetentionDetail]:
    """Retenção no wire — só existe quando houve motivo (ADR-366 §D3)."""
    if not review.retention_reason:
        return None
    return RetentionDetail(
        reason=review.retention_reason,  # type: ignore[arg-type]
        items_dropped_count=review.items_dropped_count,
    )


async def _render_review(
    db: AsyncSession, *, workspace_id: str, review: PlannerReview
) -> PlannerReviewResponse:
    """Carrega artifact + aplica tier filter + monta response — usado por GET/POST."""
    if review.outcome == ParecerOutcome.retido.value:
        # Retorna ANTES de carregar/filtrar: o artifact do retido é o placeholder de
        # `empty_needs_review_output`, e servi-lo entregaria 3 pontos fortes fabricados
        # + "Inspecione _meta.error_detail" a um cliente premium (ADR-366 §D5).
        return _build_response(review, None, 0)
    artifact = await _load_artifact(db, review.pipeline_artifact_id)
    tier = await resolve_llm_tier_async(db, workspace_id)
    content, gated = apply_tier_filter(artifact=artifact, tier=tier)  # type: ignore[arg-type]
    return _build_response(review, content, gated)


def _conflict_publish_retido() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "retained_cannot_publish",
            "message": "Parecer retido não pode ser publicado.",
        },
    )


def _conflict_publish(current_status: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "invalid_status_for_publish",
            "message": f"Parecer em status={current_status!r}; só Gerado pode publicar.",
        },
    )


def _log_published(workspace_id: str, review_id: str, immutable_hash: str) -> None:
    logger.info(
        "planner_review_published",
        extra={
            "workspace_id": workspace_id,
            "review_id": review_id,
            "immutable_hash": immutable_hash[:8],
        },
    )


# ADR-366 §D2: sem o guard do retido, publicar congelaria `immutable_hash` sobre o
# artifact placeholder — corromperia a defesa que a ADR-204 §D7 constrói.
async def _publish_if_allowed(
    db: AsyncSession,
    repo: PlannerReviewRepository,
    *,
    workspace_id: str,
    review: PlannerReview,
) -> None:
    """Transição idempotente Gerado → Publicado; retido e demais status dão 409."""
    if review.outcome == ParecerOutcome.retido.value:
        raise _conflict_publish_retido()
    if review.status == "Gerado":
        await _do_publish(db, repo, workspace_id=workspace_id, review=review)
    elif review.status != "Publicado":
        raise _conflict_publish(review.status)


async def _do_publish(
    db: AsyncSession,
    repo: PlannerReviewRepository,
    *,
    workspace_id: str,
    review: PlannerReview,
) -> None:
    """Computa hash + flippa status. Caller faz commit + refresh."""
    artifact = await _load_artifact(db, review.pipeline_artifact_id)
    immutable_hash = _compute_immutable_hash(artifact)
    await repo.publish(review.id, immutable_hash=immutable_hash)
    await db.commit()
    await db.refresh(review)
    _log_published(workspace_id, review.id, immutable_hash)


@router.post(
    "/publish",
    response_model=PlannerReviewResponse,
    status_code=status.HTTP_200_OK,
    responses=_ABSENCE_RESPONSES,
    dependencies=[Depends(require_write_role)],
)
async def publish_planner_review(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> PlannerReviewResponse:
    """Transição idempotente Gerado → Publicado. ADR-204 §D2."""
    assert VALID_PLANNER_REVIEW_STATUSES  # silence unused import
    run_id = await _resolve_run_id(db, workspace_id=workspace.id, report_id=report_id)
    repo = PlannerReviewRepository(db)
    review = await repo.get_latest_for_run(workspace.id, run_id)
    if review is None:
        raise _absent(await _absence_code(db, workspace_id=workspace.id, run_id=run_id))
    await _publish_if_allowed(db, repo, workspace_id=workspace.id, review=review)
    return await _render_review(db, workspace_id=workspace.id, review=review)
