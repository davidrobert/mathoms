"""Celery task for pipeline execution — replaces threading.Thread from Phase 2.

The core logic is identical to the former _run_pipeline_thread but:
- Scheduled via Celery instead of Thread.start()
- Publishes events via Redis Pub/Sub for WebSocket delivery
- Checks cancellation flag in DB between stages (stage-boundary cancel)
- Supports acks_late for crash recovery
- Per-stage retry with configurable retryable errors (Phase 5C.5)
"""

from __future__ import annotations

import logging
import time
import traceback
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_BRT = ZoneInfo("America/Sao_Paulo")
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
from backend.app.services.pipeline_adapter import (
    build_goals_payload_sync,
    build_tasks_payload_sync,
    build_tarefas_md_sync,
)
from backend.app.services.report_tasks_snapshot_service import (
    build_snapshot_sync,
)

logger = logging.getLogger(__name__)


def _materialize_adapter_configs(
    ws_id: str, ctx, config_dir: Path
) -> None:
    """ADR-077: materializa `goals.json` e `tarefas.md` gerados pelo
    pipeline adapter a partir do DB → filesystem do tenant.

    Scripts do pipeline (E5, E5.N, E6) continuam lendo de filesystem —
    zero refactor neles. O adapter gera payloads idênticos ao formato
    legado, mas a fonte de verdade é o DB.

    Se o workspace não tem dados no DB (ex: primeiro run antes do seed),
    preserva os arquivos originais que vieram do config_dir (fallback).

    Best-effort: exceções são logadas mas não interrompem o pipeline.
    """
    import json
    import logging

    logger = logging.getLogger("pipeline_task.materialize")

    try:
        with SyncSessionLocal() as db:
            # -- goals.json --
            # Carrega o legado como base e sobrescreve com dados do DB
            legacy_goals_path = config_dir / "goals.json"
            legacy_extras = {}
            if legacy_goals_path.exists():
                try:
                    legacy_extras = json.loads(
                        legacy_goals_path.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, OSError):
                    pass

            goals_payload = build_goals_payload_sync(
                ws_id, db=db, legacy_extras=legacy_extras
            )

            # Materializa no config_dir do context (pode ser tenant_root/config/
            # ou o config_dir global — depende do setup). Se é o global, grava
            # em tenant_root/config/ para não poluir o original.
            target_config_dir = ctx.config_dir
            target_config_dir.mkdir(parents=True, exist_ok=True)

            goals_out = target_config_dir / "goals.json"
            goals_out.write_text(
                json.dumps(goals_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info("Materialized goals.json → %s", goals_out)

            # -- tarefas.md --
            md = build_tarefas_md_sync(ws_id, db=db)
            if md.strip():
                tarefas_out = target_config_dir / "tarefas.md"
                tarefas_out.write_text(md, encoding="utf-8")
                logger.info("Materialized tarefas.md → %s", tarefas_out)
            else:
                logger.info("No tasks in DB — keeping original tarefas.md")

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to materialize adapter configs for ws=%s: %s. "
            "Pipeline will use original config files (fallback).",
            ws_id,
            exc,
        )


def _persist_llm_suggestions(
    ws_id: str, run_id: str, tenant_root: Path
) -> None:
    """ADR-074: lê `tarefas_sugeridas` do JSON de análise (E5) e persiste
    como `TaskSuggestion(source='e5n_llm')` no DB.

    Se a lista estiver vazia (caso mais comum até o LLM ser treinado para
    produzir sugestões), não faz nada. Idempotente: duplicatas são evitadas
    pelo `source_run_id` (se o mesmo run_id já tem sugestões, pula).

    Fix 2.5: Uses sync DB session instead of asyncio.run() which can crash
    inside Celery workers (especially with gevent pool) and creates
    unnecessary event loops.
    """
    import json
    import logging

    logger = logging.getLogger("pipeline_task.suggestions")

    analysis = _find_latest_analysis_json(tenant_root)
    if analysis is None:
        return

    try:
        data = json.loads(analysis.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    sugeridas = data.get("tarefas_sugeridas", [])
    if not sugeridas:
        return

    logger.info(
        "Persisting %d LLM suggestions for ws=%s run=%s",
        len(sugeridas),
        ws_id,
        run_id,
    )

    from sqlalchemy import select
    from backend.app.models.task import TaskSuggestion

    with SyncSessionLocal() as db:
        # Check idempotência: se já existem suggestions desse run, pula
        existing = db.execute(
            select(TaskSuggestion).where(
                TaskSuggestion.workspace_id == ws_id,
                TaskSuggestion.source_run_id == run_id,
            )
        ).scalars().first()
        if existing:
            logger.info("Suggestions for run %s already exist — skipping", run_id)
            return

        saved = 0
        for s in sugeridas:
            try:
                sugg = TaskSuggestion(
                    id=str(uuid.uuid4()),
                    workspace_id=ws_id,
                    source="e5n_llm",
                    source_run_id=run_id,
                    status="pending",
                    proposed_payload={
                        "title": s.get("tarefa", s.get("title", "Sugestão LLM")),
                        "category": s.get("categoria", s.get("category", "Orcamento")),
                        "priority": s.get("prioridade", s.get("priority", "R")),
                        "deadline_kind": s.get("deadline_kind", "UNSCHEDULED"),
                        "deadline_label": s.get("prazo", s.get("deadline_label")),
                        "description": s.get("descricao", s.get("description")),
                    },
                )
                db.add(sugg)
                saved += 1
            except Exception as exc:
                logger.warning("Skipping invalid suggestion: %s — %s", s, exc)

        if saved:
            db.commit()
            logger.info("Saved %d suggestions", saved)


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
        # ADR-074 §F8.3 — snapshot imutável das tasks no momento da geração.
        # Se a tabela `tasks` está vazia (ex: workspace legado pré-F8.2), vira
        # snapshot vazio — melhor que NULL pois a UI pode distinguir
        # "foto vazia" de "pré-F8.3 (fallback live)".
        try:
            tasks_snapshot = build_snapshot_sync(ws_id, db=db)
        except Exception:  # noqa: BLE001 — best-effort; nunca impede report
            tasks_snapshot = None
        try:
            from backend.app.services.premissas_snapshot import (
                build_premissas_snapshot_sync,
            )

            premissas_snapshot = build_premissas_snapshot_sync(
                ws_id, tenant_root, db
            )
        except Exception:  # noqa: BLE001
            premissas_snapshot = None
        report = Report(
            id=str(uuid.uuid4()),
            workspace_id=ws_id,
            pipeline_run_id=run_id,
            title=f"Relatório {datetime.now(_BRT).strftime('%Y-%m-%d %H:%M')}",
            html_path=str(latest),
            analysis_json_path=str(analysis_json) if analysis_json else None,
            size_bytes=latest.stat().st_size,
            tasks_snapshot_json=tasks_snapshot,
            premissas_snapshot_json=premissas_snapshot,
        )
        db.add(report)
        db.commit()


def _is_cancelled(run_id: str) -> bool:
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        return run is not None and run.status == PipelineRunStatus.cancelled


def _run_stage_with_retry(ctx, stage_name: str, _run_stage):
    """Execute a stage with configurable retry on transient errors.

    Returns (result, attempts, error_msg, tb). result is None if all retries exhausted.
    """
    retry_cfg = get_retry_config(stage_name)
    attempts = 0
    last_tb = None

    while True:
        try:
            result = _run_stage(ctx, stage_name)
            return result, attempts + 1, None, None
        except Exception as exc:
            last_tb = traceback.format_exc()
            error_msg = str(exc)[:2000]
            if retry_cfg.should_retry(attempts, error_msg):
                attempts += 1
                time.sleep(retry_cfg.delay_for_attempt(attempts - 1))
                continue
            return None, attempts + 1, error_msg, last_tb


def _resolve_use_db_artifacts(ws_id: str) -> bool:
    """A6b (ADR-106): decide se o workspace usa DBArtifactStore.

    Precedência: workspace.use_db_artifacts_override (True/False) >
                 settings.USE_DB_ARTIFACTS (global flag, default False).
    """
    from backend.app.core.config import settings

    with SyncSessionLocal() as db:
        from backend.app.models.workspace import Workspace

        ws = db.get(Workspace, ws_id)
        if ws is None:
            return settings.USE_DB_ARTIFACTS
        if ws.use_db_artifacts_override is not None:
            return bool(ws.use_db_artifacts_override)
        return settings.USE_DB_ARTIFACTS


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
    except Exception as exc:
        import logging as _logging
        _logging.getLogger("pipeline_task").warning(
            "on_failure handler could not mark run %s as failed: %s", run_id, exc
        )


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
    incremental: bool = False,
    incremental_doc_paths: list[str] | None = None,
) -> dict:
    """Execute pipeline stages sequentially as a Celery task.

    Tier-aware:
    - free tier: LLM stages auto-skipped
    - premium: LLM stages run; validation failures → StageReview + pause
    """
    import os
    import sys
    _root = str(Path(__file__).resolve().parent.parent.parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)

    from pipeline.context import WorkspaceContext
    from pipeline.orchestrator import LLM_STAGES, _run_stage

    tenant_root = Path(tenant_root_str)
    config_dir = Path(config_dir_str)

    ctx = WorkspaceContext.for_tenant(
        tenant_root, config_dir=config_dir, pipeline_run_id=run_id
    )
    ctx.incremental = incremental
    ctx.incremental_doc_paths = incremental_doc_paths or []
    ctx.ensure_dirs()

    # A6b (ADR-106): injetar DBArtifactStore quando flag ativa.
    # Abre sessão de longa duração para o store; commits após cada stage.
    # Session é fechada no finally abaixo — stages não gerenciam sua própria sessão.
    _artifact_session = None
    use_db = _resolve_use_db_artifacts(ws_id)
    if use_db:
        from backend.app.services.db_artifact_store import DBArtifactStore

        _artifact_session = SyncSessionLocal()
        ctx.artifact_store = DBArtifactStore(
            _artifact_session, workspace_id=ws_id, pipeline_run_id=run_id
        )
        logger.info(
            "pipeline_start using DBArtifactStore for run_id=%s ws_id=%s", run_id, ws_id
        )

    # Lazy-imported scripts (E0–E7) load pipeline_common — tenant-scoped paths.
    os.environ["MATHOMS_WORKSPACE_ROOT"] = str(tenant_root.resolve())

    logger.info(
        "pipeline_start run_id=%s workspace_id=%s incremental=%s "
        "incremental_paths=%d stages=%d tier=%s",
        run_id,
        ws_id,
        incremental,
        len(incremental_doc_paths or []),
        len(stages),
        tier,
    )

    # ADR-077 / F8.4: materializa payloads do adapter como arquivos no
    # tenant config dir ANTES de rodar o pipeline. Os scripts (E5, E5.N,
    # E6) continuam lendo de filesystem — zero refactor neles. O adapter
    # gera o mesmo formato de `goals.json` e `tarefas.md` a partir do DB.
    _materialize_adapter_configs(ws_id, ctx, config_dir)

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
        result, attempts, exc_error, exc_tb = _run_stage_with_retry(ctx, stage_name, _run_stage)
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
                stage_log.output_summary = {
                    "error_type": exc_error.split(":")[0].strip() if exc_error else "Exception",
                    "traceback": exc_tb,
                    "attempt_count": attempts,
                }
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
            # A6b: commit artefatos do stage antes de avançar para o próximo.
            if _artifact_session is not None:
                _artifact_session.commit()
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
            import logging as _logging
            _post_logger = _logging.getLogger("pipeline_task.post")

            try:
                from backend.app.services.document_pipeline_sync import (
                    sync_documents_pipeline_e2_status,
                )

                with SyncSessionLocal() as db:
                    run_row = db.get(PipelineRun, run_id)
                    touch_ts = (
                        run_row.completed_at
                        if run_row and run_row.completed_at
                        else datetime.now(timezone.utc)
                    )
                sync_documents_pipeline_e2_status(ws_id, tenant_root, touch_ts)
            except Exception as exc:
                _post_logger.warning("Failed to sync document E2 status: %s", exc)

            try:
                _create_report_from_output(ws_id, run_id, tenant_root)
            except Exception as exc:
                _post_logger.warning("Failed to create report from output: %s", exc)

            # ADR-074 / F8.4: persiste tarefas_sugeridas do E5.N no DB
            # (se existirem no JSON de análise).
            try:
                _persist_llm_suggestions(ws_id, run_id, tenant_root)
            except Exception as exc:
                _post_logger.warning("Failed to persist LLM suggestions: %s", exc)

    # A6b: fecha a sessão de artefatos após todo o pipeline (sucesso, falha ou pausa).
    # Commit final cobre artefatos de stages em needs_review / run cancelado.
    if _artifact_session is not None:
        try:
            _artifact_session.commit()
        except Exception:
            _artifact_session.rollback()
        finally:
            _artifact_session.close()
            logger.debug("artifact_session closed for run_id=%s", run_id)

    return {"status": "completed" if not has_failure else "failed", "run_id": run_id}
