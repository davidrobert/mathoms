"""Use case: lista runs do workspace, mais recente primeiro."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.pipeline_run._common import run_to_response
from backend.app.models.pipeline_run import PipelineRun
from backend.app.schemas.pipeline import PipelineRunListResponse


async def list_runs(workspace_id: str, *, db: AsyncSession) -> PipelineRunListResponse:
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.workspace_id == workspace_id)
        .options(selectinload(PipelineRun.stage_logs), selectinload(PipelineRun.report))
        .order_by(PipelineRun.started_at.desc())
    )
    runs = result.scalars().all()
    return PipelineRunListResponse(
        runs=[run_to_response(r) for r in runs],
        total=len(runs),
    )
