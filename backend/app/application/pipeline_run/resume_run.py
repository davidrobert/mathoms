"""Use case: retoma um run pausado para review (needs_review)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ConflictError
from backend.app.application.pipeline_run._common import fetch_run
from backend.app.models.pipeline_run import PipelineRunStatus
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.schemas.pipeline import RunActionResponse
from backend.app.services.pipeline_service import resume_pipeline_run


async def resume_run(workspace_id: str, run_id: str, *, db: AsyncSession) -> RunActionResponse:
    run = await fetch_run(workspace_id, run_id, db=db)
    if run.status != PipelineRunStatus.needs_review:
        raise ConflictError(f"Execução não está pausada para review (status: {run.status})")

    pending_reviews = await db.execute(
        select(func.count())
        .select_from(StageReview)
        .where(
            StageReview.pipeline_run_id == run_id,
            StageReview.status == StageReviewStatus.pending,
        )
    )
    if (pending_reviews.scalar() or 0) > 0:
        raise ConflictError("Existem reviews pendentes. Aprove ou edite antes de continuar.")

    try:
        resume_pipeline_run(run_id, workspace_id)
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc

    return RunActionResponse(detail="Pipeline retomado", run_id=run_id)
