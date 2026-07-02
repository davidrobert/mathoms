"""Run coordinator — sequences stages for a full run.

Bridges `pipeline.orchestrator.run_stages` to the HTTP layer: iterates the
stage list, publishes progress events, and aggregates a `RunSummaryResponse`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.contracts.runs import RunStartRequest, RunSummaryResponse
from app.contracts.stages import StageExecuteResponse
from app.services.artifact_session import (
    commit_and_close,
    open_artifact_store,
    rollback_and_close,
)
from app.services.event_publisher import publish


def run_sequence(req: RunStartRequest) -> RunSummaryResponse:
    """Execute all requested stages, emitting events per stage boundary."""
    from pipeline.context import WorkspaceContext
    from pipeline.orchestrator import LLM_STAGES, _run_stage

    started = datetime.now(timezone.utc).isoformat()
    root = Path(req.workspace_root)
    cfg = Path(req.config_dir) if req.config_dir else None
    ctx = WorkspaceContext.for_tenant(root, config_dir=cfg, pipeline_run_id=req.run_id)
    ctx.incremental = req.incremental
    ctx.incremental_doc_paths = list(req.incremental_doc_paths)
    ctx.ensure_dirs()

    total = len(req.stages)
    results: list[StageExecuteResponse] = []
    failed_stage: str | None = None

    for idx, stage in enumerate(req.stages):
        progress = int((idx / total) * 100)
        if req.skip_llm and stage in LLM_STAGES:
            publish(
                req.run_id,
                "stage_skipped",
                stage=stage,
                status="skipped",
                progress_pct=progress,
                detail={"reason": "LLM stage skipped"},
            )
            results.append(
                StageExecuteResponse(
                    stage=stage,
                    success=True,
                    detail={"skipped": True, "reason": "LLM stage skipped"},
                )
            )
            continue

        publish(req.run_id, "stage_started", stage=stage, status="running", progress_pct=progress)
        # ADR-303 D1: sessão + store por stage (espelho do loop Celery —
        # commit libera o write-lock entre stages).
        session, store = open_artifact_store(
            workspace_id=req.workspace_id,
            run_id=req.run_id,
            base_run_id=req.base_run_id,
            base_run_fallback_stages=req.base_run_fallback_stages,
        )
        try:
            ctx.artifact_store = store
            sr = _run_stage(ctx, stage)
        except BaseException:
            rollback_and_close(session)
            raise
        else:
            commit_and_close(session)
        completed = int(((idx + 1) / total) * 100)

        results.append(
            StageExecuteResponse(
                stage=sr.stage,
                success=sr.success,
                duration_ms=sr.duration_ms,
                detail=sr.detail,
                error=sr.error,
            )
        )

        if sr.success:
            publish(
                req.run_id,
                "stage_completed",
                stage=stage,
                status="completed",
                progress_pct=completed,
            )
        else:
            publish(
                req.run_id,
                "stage_failed",
                stage=stage,
                status="failed",
                error=sr.error or "unknown",
                progress_pct=completed,
            )
            failed_stage = stage
            if req.stop_on_error:
                break

    success = failed_stage is None
    publish(
        req.run_id,
        "run_completed" if success else "run_failed",
        status="completed" if success else "failed",
        progress_pct=100 if success else None,
    )

    return RunSummaryResponse(
        run_id=req.run_id,
        workspace_id=req.workspace_id,
        success=success,
        started_at=started,
        finished_at=datetime.now(timezone.utc).isoformat(),
        stages=results,
        failed_stage=failed_stage,
    )
