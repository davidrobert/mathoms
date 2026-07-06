"""Use case: aplica ação (approve/edit) em um stage review pendente."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ConflictError, ValidationError
from backend.app.application.pipeline_run._common import fetch_review, fetch_run
from backend.app.core.logging import get_logger
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.schemas.pipeline import StageReviewActionRequest, StageReviewResponse

logger = get_logger("mathoms.pipeline.review")


def _issue_counts(review: StageReview) -> tuple[int, int]:
    issues = review.validation_issues or []
    if issues:
        errors = sum(1 for i in issues if i.get("severity") == "error")
        return errors, len(issues) - errors
    lines = [ln for ln in (review.validation_errors or "").splitlines() if ln.strip()]
    return len(lines), 0


def _log_review_action(review: StageReview, *, workspace_id: str, action: str) -> None:
    """Telemetria do KR1 (A29.l1): distingue aprovação cega de resolução construtiva."""
    errors, warnings = _issue_counts(review)
    review_action = (
        "edit" if action == "edit" else ("approve_with_errors" if errors > 0 else "approve_clean")
    )
    logger.info(
        "review_action",
        extra={
            "workspace_id": workspace_id,
            "run_id": review.pipeline_run_id,
            "review_id": review.id,
            "stage": review.stage,
            "action": action,
            "review_action": review_action,
            "error_count": errors,
            "warning_count": warnings,
        },
    )


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
    _log_review_action(review, workspace_id=workspace_id, action=body.action)

    await db.commit()
    await db.refresh(review)
    return StageReviewResponse.model_validate(review)
