"""Pipeline API — trigger execution, track progress, list runs, cancel, resume, reviews (tenant-scoped, ADR-072)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.document import DOCUMENT_CLASSIFIED_OK, Document, DocumentStatus
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.report import Report as ReportModel
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.models.workspace import Workspace
from backend.app.schemas.pipeline import (
    NewDocCountResponse,
    PipelineRunListResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    RunActionResponse,
    StageReviewActionRequest,
    StageReviewResponse,
)
from backend.app.services.pipeline_service import (
    cancel_pipeline_run,
    resume_pipeline_run,
    resolve_llm_tier_async,
    start_pipeline_run,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/pipeline",
    tags=["pipeline"],
)


async def _check_no_active_run(ws_id: str, db: AsyncSession) -> None:
    """Fast-path check for an active pipeline run in the workspace.

    Serves two purposes:
      1. UX: return a descriptive 409 before doing the heavier doc-count /
         data-dir validation.
      2. Defense-in-depth: the partial unique index
         ``ux_pipeline_runs_ws_active`` (migration ``i4c5d6e7f8a9``) is the
         authoritative guard — two concurrent requests that both pass this
         check will collide on INSERT; the 2nd gets ``IntegrityError`` and
         is converted to 409 inside ``trigger_pipeline``.
    """
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


@router.post(
    "/run",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_write_role)],
)
async def trigger_pipeline(
    body: PipelineRunRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Start a pipeline execution (deterministic stages by default)."""
    await _check_no_active_run(workspace.id, db)

    doc_count_result = await db.execute(
        select(func.count()).select_from(Document).where(
            Document.workspace_id == workspace.id,
            Document.status.in_(DOCUMENT_CLASSIFIED_OK),
        )
    )
    doc_count = doc_count_result.scalar() or 0

    # Count new documents (never processed by pipeline)
    new_doc_count_result = await db.execute(
        select(func.count()).select_from(Document).where(
            Document.workspace_id == workspace.id,
            Document.status == DocumentStatus.ready,
            Document.pipeline_last_run_at.is_(None),
        )
    )
    new_doc_count = new_doc_count_result.scalar() or 0

    # Incremental mode: require new docs
    if body.incremental and new_doc_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Nenhum documento novo desde a última execução. Use 'Processar todos' para reprocessar.",
        )

    # Block pipeline if no documents are available to process
    if doc_count == 0 and not body.from_stage:
        raise HTTPException(
            status_code=400,
            detail="Nenhum documento pronto para processar. Envie documentos antes de executar o pipeline.",
        )

    # Also verify tenant data/ directory has actual files (docs may be "ready"
    # in DB but data/ can be empty if classification put them elsewhere)
    tenant_data = settings.STORAGE_ROOT / workspace.id / "data"
    has_financial_files = False
    if tenant_data.exists():
        for sub in tenant_data.iterdir():
            if sub.is_dir() and any(sub.iterdir()):
                has_financial_files = True
                break
    if not has_financial_files and not body.from_stage:
        raise HTTPException(
            status_code=400,
            detail="Nenhum documento financeiro encontrado no workspace. Os documentos podem não ter sido classificados corretamente.",
        )

    # Collect stored_paths of new documents for incremental filtering
    incremental_doc_ids: list[str] | None = None
    incremental_doc_paths: list[str] | None = None
    if body.incremental:
        new_docs_result = await db.execute(
            select(Document.id, Document.stored_path).where(
                Document.workspace_id == workspace.id,
                Document.status == DocumentStatus.ready,
                Document.pipeline_last_run_at.is_(None),
            )
        )
        new_docs_rows = new_docs_result.all()
        incremental_doc_ids = [str(r.id) for r in new_docs_rows]
        incremental_doc_paths = [r.stored_path for r in new_docs_rows if r.stored_path]
        if not incremental_doc_paths:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Modo incremental requer documentos novos com caminho de armazenamento válido. "
                    "Corrija documentos sem arquivo associado ou use 'Processar todos'."
                ),
            )

    from pipeline.orchestrator import DETERMINISTIC_ORDER, FULL_ORDER, FROM_MAP

    if body.from_stage:
        stages = FROM_MAP.get(body.from_stage)
        if stages is None:
            raise HTTPException(
                status_code=400,
                detail=f"from_stage inválido: {body.from_stage}",
            )
    elif body.skip_llm:
        stages = DETERMINISTIC_ORDER[:]
    else:
        stages = FULL_ORDER[:]

    tier = await resolve_llm_tier_async(db, workspace.id)

    run = PipelineRun(
        workspace_id=workspace.id,
        status=PipelineRunStatus.pending,
        total_documents=doc_count,
        incremental=body.incremental,
        incremental_doc_ids=incremental_doc_ids,
        tier_at_run=tier,
    )
    db.add(run)
    try:
        await db.commit()
    except IntegrityError:
        # Partial unique index `ux_pipeline_runs_ws_active` collided —
        # another request inserted a pending/running run between
        # `_check_no_active_run` and this commit. Race resolved in DB.
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma execução ativa neste workspace. Cancele ou aguarde.",
        )

    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.id == run.id)
        .options(selectinload(PipelineRun.stage_logs))
    )
    run = result.scalar_one()

    start_pipeline_run(
        run_id=run.id,
        ws_id=workspace.id,
        stages=stages,
        skip_llm=body.skip_llm,
        stop_on_error=body.stop_on_error,
        tier=tier,
        incremental=body.incremental,
        incremental_doc_paths=incremental_doc_paths or [],
    )

    return PipelineRunResponse.model_validate(run)


@router.get("/new-doc-count", response_model=NewDocCountResponse)
async def new_doc_count(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> NewDocCountResponse:
    """Count documents never processed by the pipeline (pipeline_last_run_at IS NULL)."""
    result = await db.execute(
        select(func.count()).select_from(Document).where(
            Document.workspace_id == workspace.id,
            Document.status == DocumentStatus.ready,
            Document.pipeline_last_run_at.is_(None),
        )
    )
    return NewDocCountResponse(new_count=result.scalar() or 0)


def _run_to_response(run: PipelineRun) -> PipelineRunResponse:
    r = PipelineRunResponse.model_validate(run)
    r.report_id = run.report.id if run.report else None
    return r


@router.get("/runs", response_model=PipelineRunListResponse)
async def list_runs(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """List all pipeline runs for the workspace, most recent first."""
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.workspace_id == workspace.id)
        .options(selectinload(PipelineRun.stage_logs), selectinload(PipelineRun.report))
        .order_by(PipelineRun.started_at.desc())
    )
    runs = result.scalars().all()
    return PipelineRunListResponse(
        runs=[_run_to_response(r) for r in runs],
        total=len(runs),
    )


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_run(
    run_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed status of a pipeline run including all stage logs."""
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.id == run_id, PipelineRun.workspace_id == workspace.id)
        .options(selectinload(PipelineRun.stage_logs), selectinload(PipelineRun.report))
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return _run_to_response(run)


@router.post(
    "/runs/{run_id}/cancel",
    response_model=RunActionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_write_role)],
)
async def cancel_run(
    run_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> RunActionResponse:
    """Cancel an active pipeline run (stage-boundary cancellation)."""
    result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id, PipelineRun.workspace_id == workspace.id
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

    return RunActionResponse(
        detail="Cancelamento solicitado. Pipeline parará após a etapa atual.",
        run_id=run_id,
    )


@router.post(
    "/runs/{run_id}/resume",
    response_model=RunActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_write_role)],
)
async def resume_run(
    run_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> RunActionResponse:
    """Resume a pipeline run paused for review (needs_review status)."""
    result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id, PipelineRun.workspace_id == workspace.id
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
        resume_pipeline_run(run_id, workspace.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return RunActionResponse(detail="Pipeline retomado", run_id=run_id)


@router.get("/runs/{run_id}/reviews", response_model=list[StageReviewResponse])
async def list_reviews(
    run_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """List all stage reviews for a pipeline run."""
    run_result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id, PipelineRun.workspace_id == workspace.id
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


@router.post(
    "/runs/{run_id}/reviews/{review_id}",
    response_model=StageReviewResponse,
    dependencies=[Depends(require_write_role)],
)
async def action_review(
    run_id: str,
    review_id: str,
    body: StageReviewActionRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Approve or edit a stage review."""
    run_result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id, PipelineRun.workspace_id == workspace.id
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
