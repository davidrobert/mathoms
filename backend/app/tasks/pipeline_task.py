"""Celery task for pipeline execution — replaces threading.Thread from Phase 2.

The core logic is identical to the former _run_pipeline_thread but:
- Scheduled via Celery instead of Thread.start()
- Publishes events via Redis Pub/Sub for WebSocket delivery
- Checks cancellation flag in DB between stages (stage-boundary cancel)
- Supports acks_late for crash recovery
- Per-stage retry with configurable retryable errors (Phase 5C.5)
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.app.worker import celery_app
from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.report import Report
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.services.events import (
    publish_needs_review,
    publish_run_cancelled,
    publish_run_completed,
    publish_run_failed,
    publish_stage_completed,
    publish_stage_failed,
    publish_stage_skipped,
    publish_stage_started,
)
from backend.app.services.retry_config import get_retry_config


def _find_latest_analysis_json(tenant_root: Path) -> Path | None:
    """Locate the E5 analysis JSON snapshot used for the native React report view.

    ADR-076 / F9: the rendered HTML (E6) is no longer the only consumable — the
    frontend reads the E5 JSON directly. We persist the path so GET
    /reports/{id}/data can serve it without re-running the pipeline.
    """
    e5_dir = tenant_root / "processed" / "E5_analysis"
    if not e5_dir.exists():
        return None
    candidates = sorted(
        e5_dir.glob("*-5_analysis.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _create_report_from_output(ws_id: str, run_id: str, tenant_root: Path) -> None:
    output_dir = tenant_root / "output"
    if not output_dir.exists():
        return
    html_files = sorted(output_dir.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not html_files:
        return
    latest = html_files[0]
    analysis_json = _find_latest_analysis_json(tenant_root)
    with SyncSessionLocal() as db:
        report = Report(
            id=str(uuid.uuid4()),
            workspace_id=ws_id,
            pipeline_run_id=run_id,
            title=f"Relatório {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            html_path=str(latest),
            analysis_json_path=str(analysis_json) if analysis_json else None,
            size_bytes=latest.stat().st_size,
        )
        db.add(report)
        db.commit()


def _is_cancelled(run_id: str) -> bool:
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        return run is not None and run.status == PipelineRunStatus.cancelled


def _run_stage_with_retry(ctx, stage_name: str, _run_stage):
    """Execute a stage with configurable retry on transient errors.

    Returns (result, attempts, error_msg). result is None if all retries exhausted.
    """
    retry_cfg = get_retry_config(stage_name)
    attempts = 0

    while True:
        try:
            result = _run_stage(ctx, stage_name)
            return result, attempts + 1, None
        except Exception as exc:
            error_msg = str(exc)[:2000]
            if retry_cfg.should_retry(attempts, error_msg):
                attempts += 1
                time.sleep(retry_cfg.delay_for_attempt(attempts - 1))
                continue
            return None, attempts + 1, error_msg


def _on_pipeline_task_failure(self, exc, task_id, args, kwargs, einfo):
    """BUG-003 fix: mark pipeline run as failed when the Celery task crashes
    outside the main try-catch (e.g. OOM, import error, worker killed).

    Without this, the run stays in 'pending'/'running' forever and blocks
    new runs (409 Conflict on the concurrency check).
    """
    run_id = kwargs.get("run_id") or (args[0] if args else None)
    if not run_id:
        return
    try:
        with SyncSessionLocal() as db:
            run = db.get(PipelineRun, run_id)
            if run and run.status in (
                PipelineRunStatus.pending,
                PipelineRunStatus.running,
                PipelineRunStatus.resuming,
            ):
                run.status = PipelineRunStatus.failed
                run.completed_at = datetime.now(timezone.utc)
                run.current_stage = None
                db.commit()
        publish_run_failed(run_id)
    except Exception:
        pass  # best-effort — DB may be down too


@celery_app.task(
    name="pipeline.run",
    bind=True,
    max_retries=0,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=3600,
    soft_time_limit=3000,
    on_failure=_on_pipeline_task_failure,
)
def run_pipeline_task(
    self,
    run_id: str,
    ws_id: str,
    tenant_root_str: str,
    config_dir_str: str,
    stages: list[str],
    skip_llm: bool,
    stop_on_error: bool,
    tier: str = "free",
) -> dict:
    """Execute pipeline stages sequentially as a Celery task.

    Tier-aware:
    - free tier: LLM stages auto-skipped
    - premium: LLM stages run; validation failures → StageReview + pause
    """
    import sys
    _root = str(Path(__file__).resolve().parent.parent.parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)

    from pipeline.context import WorkspaceContext
    from pipeline.orchestrator import LLM_STAGES, _run_stage

    tenant_root = Path(tenant_root_str)
    config_dir = Path(config_dir_str)

    ctx = WorkspaceContext.for_tenant(tenant_root, config_dir=config_dir)
    ctx.ensure_dirs()

    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if not run:
            return {"status": "error", "detail": "Run not found"}
        run.status = PipelineRunStatus.running
        run.tier_at_run = tier
        run.celery_task_id = self.request.id
        db.commit()

    has_failure = False
    paused_for_review = False
    total_stages = len(stages)

    for stage_idx, stage_name in enumerate(stages):
        if _is_cancelled(run_id):
            publish_run_cancelled(run_id)
            break

        is_llm = stage_name in LLM_STAGES
        should_skip_llm = skip_llm and is_llm
        should_skip_free = tier == "free" and is_llm and not skip_llm

        log_id = str(uuid.uuid4())
        stage_started_at = datetime.now(timezone.utc)
        progress_pct = int((stage_idx / total_stages) * 100)

        # --- Skip LLM stages for free tier or when explicitly skipped ---
        if should_skip_llm or should_skip_free:
            skip_status = PipelineStageStatus.skipped_free_tier if should_skip_free else PipelineStageStatus.skipped
            skip_reason = "LLM stage skipped — free tier (no API key)" if should_skip_free else "LLM stage skipped"
            with SyncSessionLocal() as db:
                run = db.get(PipelineRun, run_id)
                run.current_stage = stage_name
                db.add(PipelineStageLog(
                    id=log_id, pipeline_run_id=run_id, stage=stage_name,
                    status=skip_status, started_at=stage_started_at,
                    completed_at=stage_started_at,
                    output_summary={"skipped": True, "reason": skip_reason},
                ))
                db.commit()
            publish_stage_skipped(run_id, stage_name, skip_reason, progress_pct)
            continue

        # --- Mark stage as running ---
        with SyncSessionLocal() as db:
            run = db.get(PipelineRun, run_id)
            run.current_stage = stage_name
            db.add(PipelineStageLog(
                id=log_id, pipeline_run_id=run_id, stage=stage_name,
                status=PipelineStageStatus.running, started_at=stage_started_at,
            ))
            db.commit()

        publish_stage_started(run_id, stage_name, progress_pct)

        # --- Execute with retry ---
        start_mono = time.monotonic()
        result, attempts, exc_error = _run_stage_with_retry(ctx, stage_name, _run_stage)
        elapsed_ms = int((time.monotonic() - start_mono) * 1000)
        completed_pct = int(((stage_idx + 1) / total_stages) * 100)

        # Exception during stage (all retries exhausted)
        if result is None:
            error_msg = f"{exc_error} (after {attempts} attempt(s))" if attempts > 1 else exc_error
            with SyncSessionLocal() as db:
                stage_log = db.get(PipelineStageLog, log_id)
                stage_log.status = PipelineStageStatus.failed
                stage_log.duration_ms = elapsed_ms
                stage_log.completed_at = datetime.now(timezone.utc)
                stage_log.errors = error_msg
                run = db.get(PipelineRun, run_id)
                run.failed_at_stage = stage_name
                db.commit()
            has_failure = True
            publish_stage_failed(run_id, stage_name, exc_error or "Unknown error", progress_pct)
            if stop_on_error:
                break
            continue

        # --- Validation-based needs_review (LLM stages only) ---
        validation_has_errors = (
            result.detail
            and isinstance(result.detail, dict)
            and isinstance(result.detail.get("validation"), dict)
            and not result.detail["validation"].get("valid", True)
        )

        if result.success and validation_has_errors and is_llm:
            with SyncSessionLocal() as db:
                stage_log = db.get(PipelineStageLog, log_id)
                stage_log.status = PipelineStageStatus.needs_review
                stage_log.duration_ms = elapsed_ms
                stage_log.completed_at = datetime.now(timezone.utc)
                stage_log.output_summary = result.detail
                db.add(StageReview(
                    pipeline_run_id=run_id, stage=stage_name,
                    status=StageReviewStatus.pending,
                    original_output_json=result.detail,
                    validation_errors="\n".join(result.detail["validation"].get("errors", [])),
                ))
                run = db.get(PipelineRun, run_id)
                run.status = PipelineRunStatus.needs_review
                run.paused_at_stage = stage_name
                run.current_stage = None
                db.commit()
            publish_needs_review(run_id, stage_name)
            paused_for_review = True
            break

        # --- Normal completion or failure ---
        with SyncSessionLocal() as db:
            stage_log = db.get(PipelineStageLog, log_id)
            stage_log.status = PipelineStageStatus.completed if result.success else PipelineStageStatus.failed
            stage_log.duration_ms = elapsed_ms
            stage_log.completed_at = datetime.now(timezone.utc)
            stage_log.output_summary = result.detail
            if result.error:
                stage_log.errors = result.error
            db.commit()

        if result.success:
            publish_stage_completed(run_id, stage_name, completed_pct)
        else:
            publish_stage_failed(run_id, stage_name, result.error or "Unknown error", completed_pct)
            has_failure = True
            with SyncSessionLocal() as db:
                run = db.get(PipelineRun, run_id)
                run.failed_at_stage = stage_name
                db.commit()
            if stop_on_error:
                break

    # --- Finalize run ---
    if not paused_for_review:
        with SyncSessionLocal() as db:
            run = db.get(PipelineRun, run_id)
            if run.status not in (PipelineRunStatus.cancelled, PipelineRunStatus.needs_review):
                if has_failure:
                    run.status = PipelineRunStatus.failed
                    publish_run_failed(run_id)
                else:
                    run.status = PipelineRunStatus.completed
                    publish_run_completed(run_id)
                run.completed_at = datetime.now(timezone.utc)
                run.current_stage = None
                db.commit()

        if not has_failure:
            try:
                _create_report_from_output(ws_id, run_id, tenant_root)
            except Exception:
                pass

    return {"status": "completed" if not has_failure else "failed", "run_id": run_id}
