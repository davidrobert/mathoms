"""Use case: retoma um run pausado para review (needs_review)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ConflictError
from backend.app.application.pipeline_run._common import fetch_run
from backend.app.models.pipeline_run import PipelineRunStatus
from backend.app.schemas.pipeline import RunActionResponse
from backend.app.services.pipeline.pipeline_service import resume_pipeline_run


async def resume_run(workspace_id: str, run_id: str, *, db: AsyncSession) -> RunActionResponse:
    run = await fetch_run(workspace_id, run_id, db=db)
    if run.status != PipelineRunStatus.needs_review:
        raise ConflictError(f"Execução não está pausada para review (status: {run.status})")

    # O predicado de review sem decisão SAIU daqui (A40.l84): contá-lo nesta sessão e
    # flipar noutra era TOCTOU por construção. Agora vive em `_flip_run_to_resuming`, na
    # mesma transação do UPDATE, e alcança também quem chama o service direto. Este use
    # case não tem caminho próprio de flip, então não há a duplicação que a A40.l27 exigiu
    # do cancel — o 409 continua vindo da tradução do `ValueError` logo abaixo.
    try:
        resume_pipeline_run(run_id, workspace_id)
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc

    return RunActionResponse(detail="Pipeline retomado", run_id=run_id)
