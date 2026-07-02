"""Stage executor — thin wrapper around `pipeline.orchestrator._run_stage`.

No duplication of stage logic. The orchestrator is imported as a library
(pipeline-service lives outside the `pipeline/` package, so the framework
import ban in `dev/check_pipeline_boundaries.py` does not apply).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.contracts.stages import StageExecuteRequest, StageExecuteResponse
from app.services.artifact_session import (
    commit_and_close,
    open_artifact_store,
    rollback_and_close,
)


def run_stage_by_name(stage: str, req: StageExecuteRequest) -> StageExecuteResponse:
    """Execute a single pipeline stage with a fresh WorkspaceContext.

    ADR-303 D1: sessão + ``DBArtifactStore`` por stage, injetados no ctx
    antes de ``_run_stage`` — sem isso, qualquer stage que toque artefato
    morre em ``get_artifact_store()`` (ADR-212 PR3b).
    """
    from pipeline.orchestrator import _run_stage

    ctx = _build_context(req)
    ctx.ensure_dirs()
    session, store = open_artifact_store(
        workspace_id=req.workspace_id,
        run_id=req.run_id,
        base_run_id=req.base_run_id,
        base_run_fallback_stages=req.base_run_fallback_stages,
    )
    try:
        ctx.artifact_store = store
        result = _run_stage(ctx, stage)
    except BaseException:
        rollback_and_close(session)
        raise
    else:
        commit_and_close(session)
    return StageExecuteResponse(
        stage=result.stage,
        success=result.success,
        duration_ms=result.duration_ms,
        detail=result.detail,
        error=result.error,
    )


def _build_context(req: StageExecuteRequest):
    """Resolve a WorkspaceContext for this request.

    `config_dir` is optional; when omitted, uses `<workspace_root>/config`.
    """
    from pipeline.context import WorkspaceContext

    root = Path(req.workspace_root)
    cfg = Path(req.config_dir) if req.config_dir else None
    ctx = WorkspaceContext.for_tenant(root, config_dir=cfg, pipeline_run_id=req.run_id)
    ctx.incremental = req.incremental
    ctx.incremental_doc_paths = list(req.incremental_doc_paths)
    return ctx
