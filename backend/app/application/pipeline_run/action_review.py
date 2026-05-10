"""Use case: aplica ação (approve/edit) em um stage review pendente."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ConflictError, ValidationError
from backend.app.application.pipeline_run._common import fetch_review, fetch_run
from backend.app.models.stage_review import StageReviewStatus
from backend.app.schemas.pipeline import StageReviewActionRequest, StageReviewResponse


async def action_review(
    workspace_id: str,
    run_id: str,
    review_id: str,
    body: StageReviewActionRequest,
    *,
    db: AsyncSession,
) -> StageReviewResponse:
    await fetch_run(workspace_id, run_id, db=db)
    review = await fetch_review(run_id, review_id, db=db)

    if review.status != StageReviewStatus.pending:
        raise ConflictError(f"Review já processado (status: {review.status})")

    if body.action == "approve":
        review.status = StageReviewStatus.approved
    elif body.action == "edit":
        if not body.edited_output_json:
            raise ValidationError("edited_output_json é obrigatório para action 'edit'")
        review.status = StageReviewStatus.edited
        review.edited_output_json = body.edited_output_json

    review.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(review)
    return StageReviewResponse.model_validate(review)
