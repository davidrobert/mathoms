"""Helpers privados do agregado PipelineRun — fetch + response assembly."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.base.errors import NotFoundError
from backend.app.models.pipeline_run import PipelineRun
from backend.app.models.stage_review import StageReview
from backend.app.schemas.pipeline import PipelineRunResponse


def run_to_response(run: PipelineRun) -> PipelineRunResponse:
    r = PipelineRunResponse.model_validate(run)
    r.report_id = run.report.id if run.report else None
    return r


async def fetch_run(
    workspace_id: str, run_id: str, *, db: AsyncSession, eager: bool = False
) -> PipelineRun:
    stmt = select(PipelineRun).where(
        PipelineRun.id == run_id, PipelineRun.workspace_id == workspace_id
    )
    if eager:
        stmt = stmt.options(
            selectinload(PipelineRun.stage_logs),
            selectinload(PipelineRun.report),
        )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if run is None:
        raise NotFoundError("Execução não encontrada")
    return run


async def fetch_review(run_id: str, review_id: str, *, db: AsyncSession) -> StageReview:
    result = await db.execute(
        select(StageReview).where(
            StageReview.id == review_id,
            StageReview.pipeline_run_id == run_id,
        )
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise NotFoundError("Review não encontrado")
    return review
