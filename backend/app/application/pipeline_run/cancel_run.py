"""Use case: cancela um run ativo (stage-boundary cancellation)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ConflictError
from backend.app.application.pipeline_run._common import fetch_run
from backend.app.schemas.pipeline import RunActionResponse
from backend.app.services.pipeline.dispatch_contract import CANCELLABLE_STATUSES
from backend.app.services.pipeline.pipeline_service import cancel_pipeline_run


async def cancel_run(workspace_id: str, run_id: str, *, db: AsyncSession) -> RunActionResponse:
    run = await fetch_run(workspace_id, run_id, db=db)
    # A guarda é DUPLICADA (aqui e em `cancel_pipeline_run`), então alargar só o service
    # deixaria o endpoint respondendo 409 com o teste de service verde — verde-falso no
    # critério de aceite da A40.l27. As duas leem a MESMA constante por isso.
    if run.status not in CANCELLABLE_STATUSES:
        raise ConflictError(f"Execução não pode ser cancelada (status: {run.status})")
    cancel_pipeline_run(run_id)
    return RunActionResponse(
        detail="Cancelamento solicitado. Pipeline parará após a etapa atual.",
        run_id=run_id,
    )
