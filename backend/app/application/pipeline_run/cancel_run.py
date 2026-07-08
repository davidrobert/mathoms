"""Use case: cancela um run ativo (stage-boundary cancellation)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ConflictError
from backend.app.application.pipeline_run._common import fetch_run
from backend.app.models.pipeline_run import PipelineRunStatus
from backend.app.schemas.pipeline import RunActionResponse
from backend.app.services.pipeline.pipeline_service import cancel_pipeline_run


async def cancel_run(workspace_id: str, run_id: str, *, db: AsyncSession) -> RunActionResponse:
    run = await fetch_run(workspace_id, run_id, db=db)
    if run.status not in (PipelineRunStatus.pending, PipelineRunStatus.running):
        raise ConflictError(f"Execução não pode ser cancelada (status: {run.status})")
    cancel_pipeline_run(run_id)
    return RunActionResponse(
        detail="Cancelamento solicitado. Pipeline parará após a etapa atual.",
        run_id=run_id,
    )
