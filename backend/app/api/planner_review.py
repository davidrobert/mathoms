"""Planner review API — stub do Ato 3 retornando 404 ``not_generated_yet`` (ADR-199)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace
from backend.app.schemas.dto.planner_review import PlannerReviewResponse

router = APIRouter(
    prefix="/workspaces/{workspace_id}/reports/{report_id}/planner-review",
    tags=["planner-review"],
)


@router.get("", response_model=PlannerReviewResponse)
async def get_planner_review(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
) -> PlannerReviewResponse:
    """Retorna o parecer planejador — stub do Ato 3, sempre 404 ``not_generated_yet``."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "not_generated_yet",
            "message": "Parecer ainda não gerado para este relatório.",
        },
    )
