"""PipelineService — runs the pipeline via Celery task with DB-tracked progress.

Phase 5: migrated from threading.Thread to Celery task queue.
Cancellation is stage-boundary: sets status in DB, task checks between stages.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.models.llm_config import LLMConfig
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.events import publish_run_cancelled
from backend.app.services.storage import StorageService
from backend.app.services.vault import get_vault

logger = logging.getLogger(__name__)
_vault = get_vault()


def detect_tier(ws_id: str) -> str:
    """``premium`` only when LLMConfig exists and the API key decrypts to non-empty text."""
    with SyncSessionLocal() as db:
        cfg = db.query(LLMConfig).filter(LLMConfig.workspace_id == ws_id).first()
        if not cfg or not (cfg.api_key_encrypted or "").strip():
            return "free"
        try:
            plain = _vault.decrypt(cfg.api_key_encrypted)
        except Exception:
            return "free"
        if not plain or not str(plain).strip():
            return "free"
        return "premium"


async def resolve_llm_tier_async(db: AsyncSession, workspace_id: str) -> str:
    """Async variant of :func:`detect_tier` for FastAPI handlers (same rules)."""
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == workspace_id))
    cfg = result.scalar_one_or_none()
    if not cfg or not (cfg.api_key_encrypted or "").strip():
        return "free"
    try:
        plain = _vault.decrypt(cfg.api_key_encrypted)
    except Exception:
        return "free"
    if not plain or not str(plain).strip():
        return "free"
    return "premium"


def start_pipeline_run(
    run_id: str,
    ws_id: str,
    stages: list[str],
    *,
    skip_llm: bool = True,
    stop_on_error: bool = True,
    tier: str | None = None,
    incremental: bool = False,
    incremental_doc_paths: list[str] | None = None,
) -> str | None:
    """Launch the pipeline as a Celery task.

    Returns the Celery task ID, or None if Celery is unavailable (fallback to thread).
    """
    from backend.app.services.config_materializer import materialize_config

    if tier is None:
        tier = detect_tier(ws_id)

    storage = StorageService()
    tenant_root = storage.ensure_tenant_dirs(ws_id)

    with SyncSessionLocal() as db:
        config_dir = materialize_config(ws_id, tenant_root, db)

    try:
        from backend.app.tasks.pipeline_task import run_pipeline_task

        result = run_pipeline_task.delay(
            run_id=run_id,
            ws_id=ws_id,
            tenant_root_str=str(tenant_root),
            config_dir_str=str(config_dir),
            stages=stages,
            skip_llm=skip_llm,
            stop_on_error=stop_on_error,
            tier=tier,
            incremental=incremental,
            incremental_doc_paths=incremental_doc_paths or [],
        )
        with SyncSessionLocal() as db:
            run = db.get(PipelineRun, run_id)
            if run:
                run.celery_task_id = result.id
                db.commit()
        logger.info("Pipeline %s dispatched as Celery task %s", run_id, result.id)
        return result.id
    except Exception as exc:
        logger.warning(
            "Celery unavailable (%s), falling back to background thread for run %s",
            exc,
            run_id,
        )
        _start_fallback_thread(
            run_id,
            ws_id,
            tenant_root,
            config_dir,
            stages,
            skip_llm,
            stop_on_error,
            tier,
            incremental,
            incremental_doc_paths,
        )
        return None


def _start_fallback_thread(
    run_id,
    ws_id,
    tenant_root,
    config_dir,
    stages,
    skip_llm,
    stop_on_error,
    tier,
    incremental=False,
    incremental_doc_paths=None,
):
    """Fallback: run pipeline in a daemon thread when Celery/Redis is unavailable."""
    import threading

    from backend.app.tasks.pipeline_task import run_pipeline_task

    def _thread_target():
        run_pipeline_task(
            run_id=run_id,
            ws_id=ws_id,
            tenant_root_str=str(tenant_root),
            config_dir_str=str(config_dir),
            stages=stages,
            skip_llm=skip_llm,
            stop_on_error=stop_on_error,
            tier=tier,
            incremental=incremental,
            incremental_doc_paths=incremental_doc_paths or [],
        )

    t = threading.Thread(target=_thread_target, daemon=True, name=f"pipeline-{run_id[:8]}")
    t.start()


def resume_pipeline_run(run_id: str, ws_id: str) -> None:
    """Resume a pipeline run that was paused for review.

    Picks up from the stage *after* the paused stage.
    """
    from pipeline.orchestrator import FULL_ORDER

    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if not run or run.workspace_id != ws_id:
            raise ValueError("Run not found")
        if run.status != PipelineRunStatus.needs_review:
            raise ValueError(f"Run is not paused for review (status: {run.status})")

        paused_stage = run.paused_at_stage
        tier = run.tier_at_run or "free"

        run.status = PipelineRunStatus.resuming
        run.paused_at_stage = None
        db.commit()

    if paused_stage and paused_stage in FULL_ORDER:
        idx = FULL_ORDER.index(paused_stage)
        remaining_stages = FULL_ORDER[idx + 1 :]
    else:
        remaining_stages = []

    if not remaining_stages:
        with SyncSessionLocal() as db:
            run = db.get(PipelineRun, run_id)
            run.status = PipelineRunStatus.completed
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
        return

    start_pipeline_run(
        run_id=run_id,
        ws_id=ws_id,
        stages=remaining_stages,
        skip_llm=False,
        stop_on_error=True,
        tier=tier,
    )


def cancel_pipeline_run(run_id: str) -> bool:
    """Signal a running pipeline to cancel (stage-boundary).

    Sets status to cancelled in DB. The Celery task checks between stages.
    Also revokes the Celery task if possible.
    """
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if not run:
            return False
        if run.status not in (PipelineRunStatus.pending, PipelineRunStatus.running):
            return False

        run.status = PipelineRunStatus.cancelled
        run.completed_at = datetime.now(timezone.utc)
        db.commit()

        celery_task_id = run.celery_task_id

    if celery_task_id:
        try:
            from backend.app.worker import celery_app

            celery_app.control.revoke(celery_task_id, terminate=False)
        except Exception:
            pass

    publish_run_cancelled(run_id)
    return True


def is_run_active(run_id: str) -> bool:
    """Check if a pipeline run is still active."""
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if not run:
            return False
        return run.status in (
            PipelineRunStatus.pending,
            PipelineRunStatus.running,
            PipelineRunStatus.resuming,
        )
