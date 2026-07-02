"""Pipeline router fino — trigger/list/cancel/resume/reviews (A6e.4 · ADR-101 R15/R16)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.pipeline_run import (
    action_review as _action_review,
)
from backend.app.application.pipeline_run import (
    cancel_run as _cancel_run,
)
from backend.app.application.pipeline_run import (
    get_run as _get_run,
)
from backend.app.application.pipeline_run import (
    list_reviews as _list_reviews,
)
from backend.app.application.pipeline_run import (
    list_runs as _list_runs,
)
from backend.app.application.pipeline_run import (
    new_doc_count as _new_doc_count,
)
from backend.app.application.pipeline_run import (
    resume_run as _resume_run,
)
from backend.app.application.pipeline_run import (
    trigger_pipeline as _trigger_pipeline,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.workspace import Workspace
from backend.app.services.rate_limit import rate_limited, workspace_key
from backend.app.schemas.pipeline import (
    NewDocCountResponse,
    PipelineRunListResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    RunActionResponse,
    StageReviewActionRequest,
    StageReviewResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/pipeline",
    tags=["pipeline"],
)


@router.post(
    "/run",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[
        Depends(require_write_role),
        # W4-T04: run completo é o endpoint mais caro (LLM + CPU) da API.
        rate_limited("pipeline_run", key=workspace_key),
    ],
)
async def trigger_pipeline(
    body: PipelineRunRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> PipelineRunResponse:
    return await _trigger_pipeline(workspace.id, body, db=db)


@router.get("/new-doc-count", response_model=NewDocCountResponse)
async def new_doc_count(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> NewDocCountResponse:
    return await _new_doc_count(workspace.id, db=db)


@router.get("/runs", response_model=PipelineRunListResponse)
async def list_runs(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> PipelineRunListResponse:
    return await _list_runs(workspace.id, db=db)


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_run(
    run_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> PipelineRunResponse:
    return await _get_run(workspace.id, run_id, db=db)


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
    return await _cancel_run(workspace.id, run_id, db=db)


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
    return await _resume_run(workspace.id, run_id, db=db)


@router.get("/runs/{run_id}/reviews", response_model=list[StageReviewResponse])
async def list_reviews(
    run_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> list[StageReviewResponse]:
    return await _list_reviews(workspace.id, run_id, db=db)


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
) -> StageReviewResponse:
    return await _action_review(workspace.id, run_id, review_id, body, db=db)
