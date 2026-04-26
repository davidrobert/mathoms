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


def _classify_llm_config(cfg: LLMConfig | None, ws_id: str, *, context: str) -> str:
    """Shared tier classification with observability for silent-decrypt failures.

    Loga WARNING quando `LLMConfig` existe mas o ciphertext não decripta
    (Fernet key rotacionada / trocada) ou decripta para vazio. Sem isso,
    o pipeline degrada silenciosamente para `free tier` e todos os stages
    LLM (E1, E1.5, E2-llm, E7-review) são pulados sem rastro.
    """
    if cfg is None:
        return "free"
    ciphertext = (cfg.api_key_encrypted or "").strip()
    if not ciphertext:
        logger.warning(
            "LLMConfig sem api_key_encrypted ws=%s ctx=%s — degradando para free tier",
            ws_id,
            context,
        )
        return "free"
    try:
        plain = _vault.decrypt(ciphertext)
    except Exception as exc:
        logger.warning(
            "LLMConfig.api_key_encrypted falhou ao decriptar ws=%s ctx=%s err=%s — "
            "FERNET_KEY provavelmente rotacionada; usuário precisa re-adicionar a API key",
            ws_id,
            context,
            exc,
        )
        return "free"
    if not plain or not str(plain).strip():
        logger.warning(
            "LLMConfig.api_key_encrypted decriptou para vazio ws=%s ctx=%s — "
            "FERNET_KEY provavelmente rotacionada; usuário precisa re-adicionar a API key",
            ws_id,
            context,
        )
        return "free"
    return "premium"


def detect_tier(ws_id: str) -> str:
    """``premium`` only when LLMConfig exists and the API key decrypts to non-empty text."""
    with SyncSessionLocal() as db:
        cfg = db.query(LLMConfig).filter(LLMConfig.workspace_id == ws_id).first()
        return _classify_llm_config(cfg, ws_id, context="detect_tier")


async def resolve_llm_tier_async(db: AsyncSession, workspace_id: str) -> str:
    """Async variant of :func:`detect_tier` for FastAPI handlers (same rules)."""
    result = await db.execute(select(LLMConfig).where(LLMConfig.workspace_id == workspace_id))
    cfg = result.scalar_one_or_none()
    return _classify_llm_config(cfg, workspace_id, context="resolve_llm_tier_async")


def _dispatch_celery_task(
    run_id: str,
    ws_id: str,
    tenant_root,
    config_dir,
    stages: list[str],
    skip_llm: bool,
    stop_on_error: bool,
    tier: str,
    incremental: bool,
    incremental_doc_paths: list[str] | None,
) -> str:
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


def _prepare_run_context(ws_id: str, tier: str | None) -> tuple[str, object, object]:
    from backend.app.services.config_materializer import materialize_config

    resolved_tier = tier if tier is not None else detect_tier(ws_id)
    tenant_root = StorageService().ensure_tenant_dirs(ws_id)
    with SyncSessionLocal() as db:
        config_dir = materialize_config(ws_id, tenant_root, db)
    return resolved_tier, tenant_root, config_dir


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
    tier, tenant_root, config_dir = _prepare_run_context(ws_id, tier)
    args = (
        run_id, ws_id, tenant_root, config_dir, stages,
        skip_llm, stop_on_error, tier, incremental, incremental_doc_paths,
    )
    try:
        return _dispatch_celery_task(*args)
    except Exception as exc:
        logger.warning(
            "Celery unavailable (%s), falling back to background thread for run %s",
            exc,
            run_id,
        )
        _start_fallback_thread(*args)
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


def _flip_run_to_resuming(run_id: str, ws_id: str) -> tuple[str | None, str]:
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
    return paused_stage, tier


def _stages_after_paused(paused_stage: str | None) -> list[str]:
    from pipeline.orchestrator import FULL_ORDER

    if paused_stage and paused_stage in FULL_ORDER:
        idx = FULL_ORDER.index(paused_stage)
        return list(FULL_ORDER[idx + 1 :])
    return []


def _mark_run_completed(run_id: str) -> None:
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        run.status = PipelineRunStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        db.commit()


def resume_pipeline_run(run_id: str, ws_id: str) -> None:
    """Resume a pipeline run paused for review — picks up from the stage *after* paused."""
    paused_stage, tier = _flip_run_to_resuming(run_id, ws_id)
    remaining_stages = _stages_after_paused(paused_stage)

    if not remaining_stages:
        _mark_run_completed(run_id)
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
