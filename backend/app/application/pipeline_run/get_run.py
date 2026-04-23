"""Use case: lê status detalhado de um run (com stage_logs + report)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.pipeline_run._common import fetch_run, run_to_response
from backend.app.schemas.pipeline import PipelineRunResponse


async def get_run(workspace_id: str, run_id: str, *, db: AsyncSession) -> PipelineRunResponse:
    run = await fetch_run(workspace_id, run_id, db=db, eager=True)
    return run_to_response(run)
