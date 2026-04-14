"""Pipeline API — trigger execution, track progress, list runs, cancel, resume, reviews."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.document import Document, DocumentStatus
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.pipeline import (
    PipelineRunListResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    StageReviewActionRequest,
    StageReviewResponse,
)
from backend.app.models.llm_config import LLMConfig
from backend.app.services.pipeline_service import (
    cancel_pipeline_run,
    is_run_active,
    resume_pipeline_run,
    start_pipeline_run,
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


async def _get_workspace(user: User, db: AsyncSession) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    return ws


async def _check_no_active_run(ws_id: str, db: AsyncSession) -> None:
    """Prevent concurrent pipeline runs in the same workspace."""
    result = await db.execute(
        select(func.count()).select_from(PipelineRun).where(
            PipelineRun.workspace_id == ws_id,
            PipelineRun.status.in_([PipelineRunStatus.pending, PipelineRunStatus.running]),
        )
    )
    count = result.scalar()
    if count and count > 0:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma execução ativa neste workspace. Cancele ou aguarde.",
        )


@router.post("/run", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_pipeline(
    body: PipelineRunRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a pipeline execution (deterministic stages by default)."""
    ws = await _get_workspace(user, db)
    await _check_no_active_run(ws.id, db)

    doc_count_result = await db.execute(
        select(func.count()).select_from(Document).where(
            Document.workspace_id == ws.id,
            Document.status == DocumentStatus.ready,
        )
    )
    doc_count = doc_count_result.scalar() or 0

    from pipeline.orchestrator import DETERMINISTIC_ORDER, FROM_MAP

    if body.from_stage:
        stages = FROM_MAP.get(body.from_stage)
        if stages is None:
            raise HTTPException(
                status_code=400,
                detail=f"from_stage inválido: {body.from_stage}",
            )
    else:
        stages = DETERMINISTIC_ORDER[:]

    if body.skip_llm:
        from pipeline.orchestrator import LLM_STAGES
        stages = [s for s in stages if s not in LLM_STAGES] + [
            s for s in stages if s in LLM_STAGES
        ]

    llm_result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == ws.id))
    tier = "premium" if llm_result.scalar_one_or_none() else "free"

    run = PipelineRun(
        workspace_id=ws.id,
        status=PipelineRunStatus.pending,
        total_documents=doc_count,
        tier_at_run=tier,
    )
    db.add(run)
    await db.commit()

    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.id == run.id)
        .options(selectinload(PipelineRun.stage_logs))
    )
    run = result.scalar_one()

    start_pipeline_run(
        run_id=run.id,
        ws_id=ws.id,
        stages=stages,
        skip_llm=body.skip_llm,
        stop_on_error=body.stop_on_error,
        tier=tier,
    )

    return PipelineRunResponse.model_validate(run)


@router.get("/runs", response_model=PipelineRunListResponse)
async def list_runs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all pipeline runs for the workspace, most recent first."""
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.workspace_id == ws.id)
        .options(selectinload(PipelineRun.stage_logs))
        .order_by(PipelineRun.started_at.desc())
    )
    runs = result.scalars().all()
    return PipelineRunListResponse(
        runs=[PipelineRunResponse.model_validate(r) for r in runs],
        total=len(runs),
    )


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed status of a pipeline run including all stage logs."""
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.id == run_id, PipelineRun.workspace_id == ws.id)
        .options(selectinload(PipelineRun.stage_logs))
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return PipelineRunResponse.model_validate(run)


@router.post("/runs/{run_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an active pipeline run (stage-boundary cancellation)."""
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id, PipelineRun.workspace_id == ws.id
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    if run.status not in (PipelineRunStatus.pending, PipelineRunStatus.running):
        raise HTTPException(
            status_code=409,
            detail=f"Execução não pode ser cancelada (status: {run.status})",
        )

    cancel_pipeline_run(run_id)

    return {"detail": "Cancelamento solicitado. Pipeline parará após a etapa atual.", "run_id": run_id}


@router.post("/runs/{run_id}/resume", status_code=status.HTTP_202_ACCEPTED)
async def resume_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a pipeline run paused for review (needs_review status)."""
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id, PipelineRun.workspace_id == ws.id
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    if run.status != PipelineRunStatus.needs_review:
        raise HTTPException(
            status_code=409,
            detail=f"Execução não está pausada para review (status: {run.status})",
        )

    pending_reviews = await db.execute(
        select(func.count()).select_from(StageReview).where(
            StageReview.pipeline_run_id == run_id,
            StageReview.status == StageReviewStatus.pending,
        )
    )
    if (pending_reviews.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Existem reviews pendentes. Aprove ou edite antes de continuar.",
        )

    try:
        resume_pipeline_run(run_id, ws.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return {"detail": "Pipeline retomado", "run_id": run_id}


@router.get("/runs/{run_id}/reviews", response_model=list[StageReviewResponse])
async def list_reviews(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all stage reviews for a pipeline run."""
    ws = await _get_workspace(user, db)
    run_result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id, PipelineRun.workspace_id == ws.id
        )
    )
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    result = await db.execute(
        select(StageReview)
        .where(StageReview.pipeline_run_id == run_id)
        .order_by(StageReview.created_at)
    )
    reviews = result.scalars().all()
    return [StageReviewResponse.model_validate(r) for r in reviews]


@router.post("/runs/{run_id}/reviews/{review_id}", response_model=StageReviewResponse)
async def action_review(
    run_id: str,
    review_id: str,
    body: StageReviewActionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve or edit a stage review."""
    ws = await _get_workspace(user, db)
    run_result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id, PipelineRun.workspace_id == ws.id
        )
    )
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    result = await db.execute(
        select(StageReview).where(
            StageReview.id == review_id,
            StageReview.pipeline_run_id == run_id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review não encontrado")

    if review.status != StageReviewStatus.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Review já processado (status: {review.status})",
        )

    if body.action == "approve":
        review.status = StageReviewStatus.approved
    elif body.action == "edit":
        if not body.edited_output_json:
            raise HTTPException(
                status_code=400, detail="edited_output_json é obrigatório para action 'edit'"
            )
        review.status = StageReviewStatus.edited
        review.edited_output_json = body.edited_output_json

    review.reviewer_notes = body.reviewer_notes
    review.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(review)
    return StageReviewResponse.model_validate(review)
