"""Use case: lista stage reviews de um run."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.pipeline_run._common import fetch_run
from backend.app.models.stage_review import StageReview
from backend.app.schemas.pipeline import StageReviewResponse


async def list_reviews(
    workspace_id: str, run_id: str, *, db: AsyncSession
) -> list[StageReviewResponse]:
    await fetch_run(workspace_id, run_id, db=db)
    result = await db.execute(
        select(StageReview)
        .where(StageReview.pipeline_run_id == run_id)
        .order_by(StageReview.created_at)
    )
    reviews = result.scalars().all()
    return [StageReviewResponse.model_validate(r) for r in reviews]
