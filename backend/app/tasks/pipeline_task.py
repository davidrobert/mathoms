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
import re
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

_BRT = ZoneInfo("America/Sao_Paulo")
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.models.document import Document, DocumentType
from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.report import Report
from backend.app.models.review_reason import ReviewReason
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.schemas.dto.document.mapper import extract_e0_doc_type
from backend.app.services.pipeline.events import (
    publish_needs_review,
    publish_run_cancelled,
    publish_run_completed,
    publish_run_failed,
    publish_stage_completed,
    publish_stage_failed,
    publish_stage_skipped,
    publish_stage_started,
)
from backend.app.services.pipeline.pipeline_adapter import (
    build_tasks_payload_sync,
)
from backend.app.services.pipeline.retry_config import get_retry_config
from backend.app.services.report_tasks_snapshot_service import (
    build_snapshot_sync,
)
from backend.app.worker import celery_app

if TYPE_CHECKING:  # `pipeline.*` só é importável após _bootstrap_pipeline_sys_path()
    from pipeline.stage_outcome import StageOutcome

logger = logging.getLogger(__name__)


def _materialize_tarefas_md(ws_id: str, ctx) -> None:
    """ADR-077 + ADR-180: materializa ``tarefas.md`` — movido para o factory."""
    from backend.app.services.pipeline.run_context_factory import materialize_tarefas_md

    materialize_tarefas_md(ws_id, ctx)


def _load_active_pending(db, ws_id: str):
    """Lê pending atuais com source='e5n_llm' (dedup_key não-NULL)."""
    from sqlalchemy import select

    from backend.app.models.task import TaskSuggestion

    return (
        db.execute(
            select(TaskSuggestion).where(
                TaskSuggestion.workspace_id == ws_id,
                TaskSuggestion.source == "e5n_llm",
                TaskSuggestion.status == "pending",
                TaskSuggestion.dedup_key.is_not(None),
            )
        )
        .scalars()
        .all()
    )


def _query_recent_dismissed(db, ws_id: str, cutoff: datetime):
    from sqlalchemy import select

    from backend.app.models.task import TaskSuggestion

    return (
        db.execute(
            select(TaskSuggestion.dedup_key).where(
                TaskSuggestion.workspace_id == ws_id,
                TaskSuggestion.source == "e5n_llm",
                TaskSuggestion.status == "rejected",
                TaskSuggestion.dedup_key.is_not(None),
                TaskSuggestion.reviewed_at.is_not(None),
                TaskSuggestion.reviewed_at >= cutoff,
            )
        )
        .scalars()
        .all()
    )


def _load_recent_dismissed_keys(db, ws_id: str, *, now: datetime, window_days: int) -> set[str]:
    """dedup_keys de rejected dentro da janela — bloqueia recriação (ADR-269)."""
    from datetime import timedelta

    cutoff = now - timedelta(days=window_days)
    rows = _query_recent_dismissed(db, ws_id, cutoff)
    return {k for k in rows if k}


def _supersede_obsolete_pending(pending, new_keys: set[str], *, run_id: str, now: datetime) -> int:
    """Marca pending cujo dedup_key NÃO aparece no run novo como superseded."""
    count = 0
    for p in pending:
        if p.dedup_key in new_keys:
            continue
        p.status = "superseded"
        p.superseded_at = now
        p.superseded_by_run_id = run_id
        count += 1
    return count


def _build_pending_row(d: dict, *, ws_id: str, run_id: str):
    from backend.app.models.task import TaskSuggestion

    return TaskSuggestion(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        source="e5n_llm",
        source_run_id=run_id,
        status="pending",
        dedup_key=d["dedup_key"],
        proposed_payload=d["proposed_payload"],
    )


def _draft_skip_reason(key: str, active_keys: set[str], recent_dismissed: set[str]) -> str | None:
    if key in active_keys:
        return "active"
    if key in recent_dismissed:
        return "dismiss"
    return None


def _insert_new_drafts(
    db,
    drafts: list[dict],
    *,
    ws_id: str,
    run_id: str,
    active_keys: set[str],
    recent_dismissed: set[str],
) -> tuple[int, int]:
    """Insere drafts cujo dedup_key não está active nem foi rejeitado recente."""
    created, skipped_dismiss = 0, 0
    for d in drafts:
        reason = _draft_skip_reason(d["dedup_key"], active_keys, recent_dismissed)
        if reason == "active":
            continue
        if reason == "dismiss":
            skipped_dismiss += 1
            continue
        db.add(_build_pending_row(d, ws_id=ws_id, run_id=run_id))
        created += 1
    return created, skipped_dismiss


def _normalize_drafts(sugeridas: list, logger) -> list[dict]:
    """Normaliza lista raw do artefato E5 → drafts com dedup_key (skipa inválidos)."""
    from backend.app.services.task_suggestion_dedup import normalize_llm_draft

    drafts: list[dict] = []
    for raw in sugeridas:
        try:
            drafts.append(normalize_llm_draft(raw, source="e5n_llm"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping invalid suggestion: %s — %s", raw, exc)
    return drafts


def _apply_dedup_persist(db, drafts: list[dict], *, ws_id: str, run_id: str, now: datetime):
    """Loop principal: supersede + insert. Retorna (created, superseded, skipped_dismiss, active_kept)."""
    from backend.app.services.task_suggestion_dedup import DISMISS_RESPECT_WINDOW_DAYS

    new_keys = {d["dedup_key"] for d in drafts}
    pending = _load_active_pending(db, ws_id)
    superseded = _supersede_obsolete_pending(pending, new_keys, run_id=run_id, now=now)
    active_keys = {p.dedup_key for p in pending if p.status == "pending"}
    recent_dismissed = _load_recent_dismissed_keys(
        db, ws_id, now=now, window_days=DISMISS_RESPECT_WINDOW_DAYS
    )
    created, skipped_dismiss = _insert_new_drafts(
        db,
        drafts,
        ws_id=ws_id,
        run_id=run_id,
        active_keys=active_keys,
        recent_dismissed=recent_dismissed,
    )
    return created, superseded, skipped_dismiss, len(active_keys)


def _log_persist_summary(logger, ws_id, run_id, drafts, stats) -> None:
    created, superseded, skipped_dismiss, active_kept = stats
    logger.info(
        "task_suggestion.persist ws=%s run=%s drafts=%d created=%d "
        "superseded=%d skipped_dismiss=%d active_kept=%d",
        ws_id,
        run_id,
        len(drafts),
        created,
        superseded,
        skipped_dismiss,
        active_kept,
    )


def _read_e5_sugeridas(ws_id: str, run_id: str) -> list | None:
    """None se artefato E5 ausente; lista (possivelmente vazia) caso contrário."""
    artifact = _find_latest_analysis_artifact(ws_id, run_id)
    if artifact is None:
        return None
    return (artifact["content_json"] or {}).get("tarefas_sugeridas", []) or []


def _persist_llm_suggestions(ws_id: str, run_id: str, tenant_root: Path) -> None:
    """ADR-074 + ADR-269: soft-supersede + dedup_key normalizado a partir de tarefas_sugeridas (E5)."""
    import logging

    logger = logging.getLogger("pipeline_task.suggestions")
    sugeridas = _read_e5_sugeridas(ws_id, run_id)
    if sugeridas is None:
        return
    drafts = _normalize_drafts(sugeridas, logger)
    now = datetime.now(timezone.utc)
    with SyncSessionLocal() as db:
        stats = _apply_dedup_persist(db, drafts, ws_id=ws_id, run_id=run_id, now=now)
        if stats[0] or stats[1]:
            db.commit()
        _log_persist_summary(logger, ws_id, run_id, drafts, stats)


def _persist_aggregate_suggestions(ws_id: str, run_id: str) -> None:
    """ADR-153: re-gera Suggestions a partir do snapshot E5 do Report (idempotente)."""
    # Sync espelha o use case async `regenerate_for_report` — mesmo motivo de
    # `_persist_llm_suggestions`: asyncio.run() em gevent crasha.
    # Dedup via `dedup_key` segue ADR-153 §2.
    import logging

    from sqlalchemy import select

    from backend.app.models.suggestion import Suggestion
    from backend.app.schemas.dto.decision.mapper import brl_to_cents
    from pipeline.domain.services.suggestion_generator import (
        DISMISS_RESPECT_WINDOW_DAYS,
        SUGGESTION_CAP,
        SuggestionGenerator,
        SuggestionGeneratorConfig,
    )

    sugg_logger = logging.getLogger("pipeline_task.suggestions_aggregate")

    artifact = _find_latest_analysis_artifact(ws_id, run_id)
    if artifact is None:
        return

    snapshot = artifact.get("content_json")
    if not isinstance(snapshot, dict) or not snapshot:
        return

    drafts = SuggestionGenerator(SuggestionGeneratorConfig()).generate(snapshot)[:SUGGESTION_CAP]
    if not drafts:
        sugg_logger.info("regen_suggestions: ws=%s run=%s no_drafts", ws_id, run_id)
        return

    with SyncSessionLocal() as db:
        report = (
            db.execute(
                select(Report).where(
                    Report.workspace_id == ws_id,
                    Report.pipeline_run_id == run_id,
                )
            )
            .scalars()
            .first()
        )
        if report is None:
            sugg_logger.warning(
                "regen_suggestions_skipped: no Report row for ws=%s run=%s",
                ws_id,
                run_id,
            )
            return

        now = datetime.now(timezone.utc)
        created = 0
        for draft in drafts:
            existing = (
                db.execute(
                    select(Suggestion)
                    .where(
                        Suggestion.workspace_id == ws_id,
                        Suggestion.dedup_key == draft.dedup_key,
                    )
                    .order_by(Suggestion.created_at.desc())
                )
                .scalars()
                .all()
            )
            if _suggestion_should_skip(
                list(existing), now=now, window_days=DISMISS_RESPECT_WINDOW_DAYS
            ):
                continue
            db.add(
                Suggestion(
                    workspace_id=ws_id,
                    report_id=report.id,
                    section_id=draft.section_id,
                    kind=draft.kind,
                    origin=draft.origin,
                    severity=draft.severity,
                    title=draft.title,
                    rationale=draft.rationale,
                    amount_brl_cents=brl_to_cents(draft.amount_brl),
                    dedup_key=draft.dedup_key,
                    status="Pendente",
                )
            )
            created += 1
        if created:
            db.commit()
            sugg_logger.info(
                "regen_suggestions: ws=%s run=%s created=%d total_drafts=%d",
                ws_id,
                run_id,
                created,
                len(drafts),
            )


def _suggestion_should_skip(existing, *, now, window_days):
    # Política de dedup ADR-153 §2 — espelha
    # ``backend.app.application.suggestions.regenerate_for_report._should_skip``.
    # Duplicação aceita: chamadores em sync (Celery worker) e async (endpoint).
    return any(
        _suggestion_row_blocks(row, now=now, window_days=window_days) for row in existing or []
    )


def _suggestion_row_blocks(row, *, now, window_days):
    if row.status in ("Pendente", "Aceita", "Modificada"):
        return True
    if row.status != "Descartada":
        return False
    if row.dismissed_at is None:
        return True
    age_days = (now - row.dismissed_at).total_seconds() / 86400
    return age_days < window_days


def _find_latest_analysis_artifact(ws_id: str, run_id: str):
    """Localiza o artefato E5 (stage legado ou descritivo, key ``analise_financeira``)
    para o run especificado. ADR-131: substitui ``_find_latest_analysis_json``
    (filesystem-based) — o relatório passa a referenciar o artifact por FK.

    Retorna o ``PipelineArtifact`` ou ``None``. Caller é responsável por
    abrir/fechar a sessão; passamos a row ainda vinculada à sessão de
    abertura para que o caller possa usar ``row.id``.
    """
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from pipeline.artifact_store import stage_aliases
    from pipeline.domain.services.e5_serialization import (
        E5_ARTIFACT_KEY,
        E5_OUTPUT_STAGE,
    )

    with SyncSessionLocal() as db:
        row = (
            db.query(PipelineArtifact)
            .filter(
                PipelineArtifact.workspace_id == ws_id,
                PipelineArtifact.pipeline_run_id == run_id,
                # legado E5 ↔ descritivo analyze_finances (ADR-093, janela F9)
                PipelineArtifact.stage.in_(stage_aliases(E5_OUTPUT_STAGE)),
                PipelineArtifact.artifact_key == E5_ARTIFACT_KEY,
            )
            .one_or_none()
        )
        if row is None or not row.content_json:
            return None
        # Captura os campos antes de fechar a sessão (objeto detacha).
        from backend.app.services.security.crypto import read_artifact_content

        return {"id": row.id, "content_json": read_artifact_content(row.content_json)}


def _create_report_from_output(ws_id: str, run_id: str, tenant_root: Path) -> None:
    # ADR-131: Report referencia o artefato E5 por FK (analysis_artifact_id).
    # Sem artifact no DB, não há nada para o relatório React consumir.
    artifact = _find_latest_analysis_artifact(ws_id, run_id)
    if artifact is None:
        logger.error(
            "report_creation_skipped: no E5 analysis artifact in DB for ws=%s run=%s",
            ws_id,
            run_id,
        )
        return
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

            premissas_snapshot = build_premissas_snapshot_sync(ws_id, tenant_root, db)
        except Exception:  # noqa: BLE001
            premissas_snapshot = None
        analysis_content = artifact.get("content_json") or {}
        period_value = analysis_content.get("periodo_dados") or analysis_content.get("data_analise")
        score, patrimonio_liquido = Report.denorm_from_analysis(analysis_content)
        report = Report(
            id=str(uuid.uuid4()),
            workspace_id=ws_id,
            pipeline_run_id=run_id,
            title=f"Relatório {datetime.now(_BRT).strftime('%Y-%m-%d %H:%M')}",
            period=period_value if isinstance(period_value, str) else None,
            analysis_artifact_id=artifact["id"],
            tasks_snapshot_json=tasks_snapshot,
            premissas_snapshot_json=premissas_snapshot,
            score=score,
            patrimonio_liquido=patrimonio_liquido,
        )
        db.add(report)
        try:
            db.commit()
        except IntegrityError:
            # REL-03 — índice único (workspace_id, pipeline_run_id): um
            # redelivery concorrente já criou o Report deste run. Idempotente:
            # rollback e segue (o relatório existente é válido).
            db.rollback()
            logger.warning(
                "report_already_exists ws=%s run=%s — idempotent skip (REL-03)",
                ws_id,
                run_id,
            )


def _is_cancelled(run_id: str) -> bool:
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        return run is not None and run.status == PipelineRunStatus.cancelled


def _retry_parked_documents(ws_id: str, tenant_root: Path) -> None:
    """C8/ADR-329 + A37.l3: re-classifica docs parkados por skip transitório no início de um run premium (best-effort — falha nunca aborta o run; sync/gevent-safe)."""
    from backend.app.services.documents.document_reclassify_retry import (
        retry_parked_documents_sync,
    )
    from backend.app.services.storage import StorageService

    try:
        with SyncSessionLocal() as db:
            stats = retry_parked_documents_sync(
                ws_id, db=db, storage=StorageService(), tenant_root=tenant_root
            )
            if stats["reclassified"] or stats["relocated"]:
                db.commit()
    except Exception:  # noqa: BLE001 — best-effort; nunca impede o run
        logger.warning("reclassify_retry_failed ws=%s", ws_id, exc_info=True)
        return
    # A37.l3 — contadores retried/no_file/skipped/relocated: gap não pode ser invisível.
    if any(stats.values()):
        logger.info("reclassify_retry ws=%s %s", ws_id, stats)


def _is_schema_validation_error(exc: Exception) -> bool:
    """Erro de contrato é determinístico — nunca retryable (ADR-284); sem a guarda, stages com ``retryable_errors`` casariam substring do texto e queimariam backoff."""
    import jsonschema

    return isinstance(exc, jsonschema.ValidationError)


def _run_stage_with_retry(ctx, stage_name: str, _run_stage):
    """Execute a stage with configurable retry on transient errors.

    Returns (result, attempts, error_msg, tb, reason_class). result is None if all
    retries exhausted; reason_class is derived from the live exception OBJECT.
    """
    # `reason_class` sai daqui, e não do texto de `error_msg`, porque a ADR-357
    # §Delta item 1 proíbe re-derivar a classe por match de string sobre a
    # mensagem. Este é o último ponto em que o objeto de exceção existe.
    from backend.app.services.pipeline.stage_failure_reason import (
        StageFailureReason,
        reason_from_exception,
    )

    retry_cfg = get_retry_config(stage_name)
    attempts = 0
    last_tb = None

    while True:
        try:
            result = _run_stage(ctx, stage_name)
            return result, attempts + 1, None, None, StageFailureReason.unknown.value
        except Exception as exc:
            last_tb = traceback.format_exc()
            error_msg = str(exc)[:2000]
            if not _is_schema_validation_error(exc) and retry_cfg.should_retry(attempts, error_msg):
                attempts += 1
                time.sleep(retry_cfg.delay_for_attempt(attempts - 1))
                continue
            return None, attempts + 1, error_msg, last_tb, reason_from_exception(exc).value


_CRASH_RUN_STATUSES = (
    PipelineRunStatus.pending,
    PipelineRunStatus.running,
    PipelineRunStatus.resuming,
)

# REL-03 — estados terminais: um redelivery não deve re-executar o pipeline.
# ``running``/``resuming``/``pending``/``needs_review`` ficam de fora de
# propósito (crash-recovery e resume legítimos precisam re-entrar).
_TERMINAL_RUN_STATUSES = (
    PipelineRunStatus.completed,
    PipelineRunStatus.failed,
    PipelineRunStatus.partial_failure,
    PipelineRunStatus.cancelled,
)

# A37.l12 (EXEC-01) — marcador de conclusão de stage por (run_id, stage).
# Redelivery (acks_late; crash/sleep do host) re-executa a task do zero; sem
# o marcador, stage LLM já concluído re-paga a call e duplica stage_logs.
# "Artifact existe" não serve de marcador: redelivery mid-stage (crash antes
# do write) não tem artifact E precisa re-executar. O stage_log terminal é
# gravado APÓS o commit dos artefatos — marker ⇒ artefatos persistidos.
_STAGE_DONE_STATUSES = (
    PipelineStageStatus.completed,
    PipelineStageStatus.skipped,
    PipelineStageStatus.skipped_free_tier,
    # ADR-357 §4 — `degraded` terminou; só não entregou. Sem ele aqui, o
    # redelivery Celery re-executa e RE-PAGA o stage LLM já cobrado (US$ 0,48 no
    # incidente de origem), reintroduzindo no ramo degradado a regressão que a
    # A37.l12 fechou.
    PipelineStageStatus.degraded,
)

# Tradução desfecho → status persistido (ADR-357). Mora em `backend/` porque toca
# o enum SQLAlchemy; a DERIVAÇÃO do desfecho é pura e mora em
# `pipeline/stage_outcome.py`.
#
# `skipped` mapeia para `completed` de propósito. `PipelineStageStatus.skipped` já
# significa outra coisa — o orquestrador decidiu NÃO rodar o stage (tier free /
# `skip_llm`), gravado por `_record_stage_skip` antes da execução. Já
# `{"skipped": True}` é no-op declarado pelo próprio stage (5 early-returns do
# parecer, `extract_*` sem documento) e hoje grava `completed`. Conflacionar os
# dois flipparia status e evento WS de caso que ship hoje; a ADR-357 §2 manda
# preservar o default atual.
# Chaveado por string, não pelo membro do enum: `pipeline.*` só é importável
# depois de `_bootstrap_pipeline_sys_path()`, então import module-level aqui
# quebraria o worker. `StageOutcome` é `str, Enum` e hashea como a string.
_STAGE_STATUS_BY_OUTCOME: dict[str, PipelineStageStatus] = {
    "completed": PipelineStageStatus.completed,
    "skipped": PipelineStageStatus.completed,
    "degraded": PipelineStageStatus.degraded,
    "failed": PipelineStageStatus.failed,
}


def _find_stage_completion_marker(run_id: str, stage_name: str) -> dict | None:
    """Retorna ``{log_id, status}`` do stage_log terminal para (run_id, stage)."""
    with SyncSessionLocal() as db:
        row = (
            db.execute(
                select(PipelineStageLog)
                .where(
                    PipelineStageLog.pipeline_run_id == run_id,
                    PipelineStageLog.stage == stage_name,
                    PipelineStageLog.status.in_(_STAGE_DONE_STATUSES),
                )
                .order_by(PipelineStageLog.started_at.desc())
            )
            .scalars()
            .first()
        )
        if row is None:
            return None
        return {"log_id": row.id, "status": row.status}


def _publish_redelivered_stage_event(
    run_id: str, stage_name: str, status: PipelineStageStatus, completed_pct: int
) -> None:
    if status == PipelineStageStatus.completed:
        publish_stage_completed(run_id, stage_name, completed_pct)
        return
    # Reusa `stage_skipped` (a §Consequências da ADR-357 recusa evento novo), mas
    # carrega o status REAL do marcador: com `degraded` em `_STAGE_DONE_STATUSES`,
    # anunciar `status="skipped"` faria o frontend ler skip onde houve degradação.
    reason = (
        "stage degradado neste run (redelivery)"
        if status == PipelineStageStatus.degraded
        else "LLM stage skipped (redelivery)"
    )
    publish_stage_skipped(run_id, stage_name, reason, completed_pct, status=status.value)


def _log_stage_redelivered(run_id: str, stage_name: str, log_id: str) -> None:
    logger.info(
        "stage_redelivery_skip: stage já concluído neste run — reusa artefatos",
        extra={
            "event": "mathoms.pipeline.stage_redelivered",
            "run_id": run_id,
            "stage": stage_name,
            "redelivered": True,
            "reused_stage_log_id": log_id,
        },
    )


def _record_stage_redelivery_skip(
    run_id: str, stage_name: str, marker: dict, completed_pct: int
) -> None:
    """EXEC-01: ``redelivered=true`` na telemetria do stage_log reusado + evento WS."""
    with SyncSessionLocal() as db:
        stage_log = db.get(PipelineStageLog, marker["log_id"])
        summary = dict(stage_log.output_summary or {})
        summary["redelivered"] = True
        stage_log.output_summary = summary
        db.commit()
    _log_stage_redelivered(run_id, stage_name, marker["log_id"])
    _publish_redelivered_stage_event(run_id, stage_name, marker["status"], completed_pct)


def _mark_running_stage_log_failed(db, run_id: str, stage: str, exc, now) -> None:
    """Marca o stage_log em ``status=running`` como ``failed`` — paridade com ``_record_stage_exception``."""
    from sqlalchemy import select

    log = db.execute(
        select(PipelineStageLog)
        .where(
            PipelineStageLog.pipeline_run_id == run_id,
            PipelineStageLog.stage == stage,
            PipelineStageLog.status == PipelineStageStatus.running,
        )
        .order_by(PipelineStageLog.started_at.desc())
    ).scalar_one_or_none()
    if log is None:
        return
    log.status = PipelineStageStatus.failed
    log.completed_at = now
    if log.started_at is not None:
        started = log.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        log.duration_ms = int((now - started).total_seconds() * 1000)
    log.errors = f"Task crashed: {exc!s}"[:2000]


def _apply_task_crash_to_run(run, exc, now, db) -> None:
    """Aplica BUG-003 + preserva ``failed_at_stage``/stage_log para retomada via UI."""
    if run.current_stage and not run.failed_at_stage:
        _mark_running_stage_log_failed(db, run.id, run.current_stage, exc, now)
        run.failed_at_stage = run.current_stage
    run.status = PipelineRunStatus.failed
    run.completed_at = now
    run.current_stage = None


def _on_pipeline_task_failure(self, exc, task_id, args, kwargs, einfo):
    """BUG-003 — marca run como ``failed`` quando o Celery task crasha fora do try/catch interno (OOM, import error, worker killed)."""
    run_id = kwargs.get("run_id") or (args[0] if args else None)
    if not run_id:
        return
    now = datetime.now(timezone.utc)
    try:
        with SyncSessionLocal() as db:
            run = db.get(PipelineRun, run_id)
            if run and run.status in _CRASH_RUN_STATUSES:
                _apply_task_crash_to_run(run, exc, now, db)
                db.commit()
        publish_run_failed(run_id)
    except Exception as exc:
        import logging as _logging

        _logging.getLogger("pipeline_task").warning(
            "on_failure handler could not mark run %s as failed: %s", run_id, exc
        )


def _bootstrap_pipeline_sys_path() -> None:
    """Garante que `pipeline.*` seja importável no worker Celery."""
    import sys

    _root = str(Path(__file__).resolve().parent.parent.parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)


def _setup_run_context(
    run_id: str,
    ws_id: str,
    tenant_root: Path,
    config_dir: Path,
    incremental: bool,
    incremental_doc_paths: list[str] | None,
    skip_llm: bool = False,
):
    """Cria WorkspaceContext hidratado (delegado a ``run_context_factory``).

    Retorna ``(ctx, config_store_session)`` — a sessão long-lived que
    respaldou o ``DBConfigStore`` é devolvida ao caller para fechamento
    ao fim do run. A hidratação canônica (config_store + overrides +
    resolvers ADR-215/219/222 + imoveis_no_if + budget hooks ADR-173)
    vive em ``backend/app/services/pipeline/run_context_factory.py`` — fonte
    única dos três executores (Celery, HTTP, CLI). ``stage_duration_estimates``
    permanece Celery-only (só alimenta progresso WS).
    """
    from backend.app.services.pipeline.run_context_factory import build_hydrated_context

    hydrated = build_hydrated_context(
        ws_id=ws_id,
        tenant_root=tenant_root,
        run_id=run_id,
        config_dir=config_dir,
        incremental=incremental,
        incremental_doc_paths=incremental_doc_paths,
        skip_llm=skip_llm,
    )
    ctx = hydrated.ctx
    ctx.stage_duration_estimates = _load_stage_duration_estimates(ws_id)
    return ctx, hydrated.config_store_session


def _close_config_store_session(session) -> None:
    """Fecha a sessão long-lived do ``DBConfigStore`` ao fim do run (A7.1)."""
    if session is None:
        return
    try:
        session.close()
    except Exception as exc:
        logger.warning("config_store_session close failed: %s", exc)


def _load_stage_duration_estimates(ws_id: str) -> dict[str, int]:
    """Carrega medianas cacheadas (ADR-119 item 5). Falha aberta: dict vazio."""
    from backend.app.services.pipeline.stage_duration_estimator import get_cached_stage_estimates

    session = SyncSessionLocal()
    try:
        return get_cached_stage_estimates(session, ws_id)
    except Exception as exc:
        logger.warning("stage_duration_estimates load failed for ws=%s: %s", ws_id, exc)
        return {}
    finally:
        session.close()


def _open_artifact_session(
    ws_id: str,
    run_id: str,
    base_run_id: str | None = None,
    base_run_fallback_stages: frozenset[str] = frozenset(),
):
    """Abre sessão nova + DBArtifactStore. Chamado por-stage pelo loop."""
    # base_run_id + base_run_fallback_stages ativam o fallback run-pinado para
    # runs com from_stage (ADR-291); defaults preservam full/incremental/resume.
    from backend.app.services.storage.db_artifact_store import DBArtifactStore

    session = SyncSessionLocal()
    store = DBArtifactStore(
        session,
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        base_run_id=base_run_id,
        base_run_fallback_stages=base_run_fallback_stages,
    )
    return session, store


def _commit_and_close_artifact_session(session) -> None:
    """Commit+close de uma sessão por-stage. Rollback se commit falhar."""
    if session is None:
        return
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _rollback_and_close_artifact_session(session) -> None:
    """Rollback+close — usado quando stage falha antes do commit."""
    if session is None:
        return
    try:
        session.rollback()
    finally:
        session.close()


def _mark_run_started(run_id: str, tier: str, celery_task_id: str) -> bool:
    """Muda ``PipelineRun.status`` para ``running``. ``False`` se o run não
    existe ou já está terminal (REL-03: redelivery não re-executa)."""
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if not run:
            return False
        if run.status in _TERMINAL_RUN_STATUSES:
            logger.warning(
                "redelivery_of_terminal_run run_id=%s status=%s", run_id, run.status.value
            )
            return False
        run.status = PipelineRunStatus.running
        run.tier_at_run = tier
        run.celery_task_id = celery_task_id
        run.last_heartbeat_at = datetime.now(timezone.utc)
        db.commit()
    return True


def _record_stage_skip(
    run_id: str,
    stage_name: str,
    log_id: str,
    stage_started_at,
    should_skip_free: bool,
    progress_pct: int,
) -> None:
    skip_status = (
        PipelineStageStatus.skipped_free_tier if should_skip_free else PipelineStageStatus.skipped
    )
    skip_reason = (
        "LLM stage skipped — free tier (no API key)" if should_skip_free else "LLM stage skipped"
    )
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        run.current_stage = stage_name
        db.add(
            PipelineStageLog(
                id=log_id,
                pipeline_run_id=run_id,
                stage=stage_name,
                status=skip_status,
                started_at=stage_started_at,
                completed_at=stage_started_at,
                output_summary={"skipped": True, "reason": skip_reason},
                executor_revision=settings.executor_revision,
            )
        )
        db.commit()
    publish_stage_skipped(run_id, stage_name, skip_reason, progress_pct)


def _record_stage_running(
    run_id: str,
    stage_name: str,
    log_id: str,
    stage_started_at,
    progress_pct: int,
) -> None:
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        run.current_stage = stage_name
        # ADR-172: heartbeat atualizado em cada stage start.
        run.last_heartbeat_at = stage_started_at
        db.add(
            PipelineStageLog(
                id=log_id,
                pipeline_run_id=run_id,
                stage=stage_name,
                status=PipelineStageStatus.running,
                started_at=stage_started_at,
                executor_revision=settings.executor_revision,
            )
        )
        db.commit()
    publish_stage_started(run_id, stage_name, progress_pct)


def _record_stage_exception(
    run_id: str,
    stage_name: str,
    log_id: str,
    attempts: int,
    exc_error: str | None,
    exc_tb: str | None,
    elapsed_ms: int,
    progress_pct: int,
    outcome: "StageOutcome",
    reason_class: str = "unknown",
) -> None:
    error_msg = f"{exc_error} (after {attempts} attempt(s))" if attempts > 1 else exc_error
    with SyncSessionLocal() as db:
        stage_log = db.get(PipelineStageLog, log_id)
        stage_log.status = _STAGE_STATUS_BY_OUTCOME[outcome]
        stage_log.duration_ms = elapsed_ms
        stage_log.completed_at = datetime.now(timezone.utc)
        stage_log.errors = error_msg
        stage_log.output_summary = {
            "error_type": exc_error.split(":")[0].strip() if exc_error else "Exception",
            "traceback": exc_tb,
            "attempt_count": attempts,
            "reason_class": reason_class,
        }
        # Ver §3 em `_record_stage_result`: degradação não popula campo de falha.
        if outcome == "failed":
            run = db.get(PipelineRun, run_id)
            run.failed_at_stage = stage_name
        db.commit()
    publish_stage_failed(run_id, stage_name, exc_error or "Unknown error", progress_pct)


# Cap de rows por (run, code) — proteção contra row explosion (ADR-272 Fase 2).
# Consolidamos para 1 row por (run, code) somando occurrence_count cross-doc; o cap
# é defensivo (há só 6 ReviewReasonCode, então <=6 rows por run na prática).
_REVIEW_REASON_ROW_CAP = 50


def _existing_review_reason(db, *, run_id: str, workspace_id: str, code: str):
    """Row já materializada para (run, code) — autoflush torna add anterior visível na mesma transação."""
    from sqlalchemy import select

    return db.execute(
        select(ReviewReason).where(
            ReviewReason.workspace_id == workspace_id,
            ReviewReason.pipeline_run_id == run_id,
            ReviewReason.code == code,
        )
    ).scalar_one_or_none()


def _new_review_reason_row(
    payload: dict, *, run_id: str, workspace_id: str, stage_name: str, inc: int
):
    """Constrói row ReviewReason a partir do dict projetado pelo stage."""
    return ReviewReason(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        stage=stage_name,
        code=payload["code"],
        artifact_key=payload.get("artifact_key", "") or "",
        document_id=payload.get("document_id"),
        offending_value=payload.get("offending_value", "") or "",
        expected=payload.get("expected", "") or "",
        message=payload.get("message", "") or "",
        occurrence_count=inc,
    )


def _apply_one_reason(
    db, payload: dict, *, run_id: str, workspace_id: str, stage_name: str, can_insert: bool
) -> bool:
    """Bump (run, code) existente ou insere nova row se can_insert. Retorna True se inseriu."""
    code = payload.get("code")
    if not code:
        return False
    inc = int(payload.get("occurrence_count", 1) or 1)
    existing = _existing_review_reason(db, run_id=run_id, workspace_id=workspace_id, code=code)
    if existing is not None:
        existing.occurrence_count += inc
        return False
    if not can_insert:
        return False
    db.add(
        _new_review_reason_row(
            payload, run_id=run_id, workspace_id=workspace_id, stage_name=stage_name, inc=inc
        )
    )
    return True


def _materialize_review_reasons(
    db, *, run_id: str, workspace_id: str, stage_name: str, reasons: list[dict]
) -> int:
    """Materializa review_reasons (ADR-272 Fase 2): 1 row por (run, code), soma occurrence_count. Retorna nº inseridas."""
    inserted = 0
    for payload in reasons:
        if _apply_one_reason(
            db,
            payload,
            run_id=run_id,
            workspace_id=workspace_id,
            stage_name=stage_name,
            can_insert=inserted < _REVIEW_REASON_ROW_CAP,
        ):
            inserted += 1
    return inserted


_ISSUE_CAP_PER_CODE = 20
# Prefixo content-addressed dos filenames/keys de artefato (ADR-084): sha256[:12].
_HASH_PREFIX_RE = re.compile(r"^[0-9a-f]{12}(?=_)")


def _document_identity(doc: Document) -> dict:
    """Campos que a UI de review precisa para rótulo legível
    "Instituição · Tipo · Período" (A32.l6) — nunca o hash cru."""
    doc_type = doc.doc_type
    return {
        "document_id": doc.id,
        "doc_bank_code": doc.bank_code,
        "doc_type": doc_type.value if isinstance(doc_type, DocumentType) else doc_type,
        "doc_e0_type": extract_e0_doc_type(doc.classification_meta),
        "doc_period": doc.period,
    }


def _identity_filters(prefixes: set[str], doc_ids: set[str]) -> list:
    filters = [Document.content_hash.like(f"{p}%") for p in prefixes]
    if doc_ids:
        filters.append(Document.id.in_(doc_ids))
    return filters


def _resolve_document_identities(
    db, workspace_id: str, reasons: list[dict]
) -> tuple[dict[str, dict], dict[str, dict]]:
    """(artifact_key → identity, document_id → identity) via prefixo content_hash[:12]
    (ADR-308 §5) e FK explícita; quem conhece ``documents`` é este boundary."""
    keys = {r.get("artifact_key") or "" for r in reasons} - {""}
    explicit_ids = {r.get("document_id") for r in reasons if r.get("document_id")}
    prefixes = {m.group(0) for k in keys if (m := _HASH_PREFIX_RE.match(k))}
    if not prefixes and not explicit_ids:
        return {}, {}
    docs = (
        db.query(Document)
        .filter(
            Document.workspace_id == workspace_id,
            or_(*_identity_filters(prefixes, explicit_ids)),
        )
        .all()
    )
    by_id = {d.id: _document_identity(d) for d in docs}
    return _identities_by_key(docs, keys, by_id), by_id


def _identities_by_key(docs: list, keys: set[str], by_id: dict[str, dict]) -> dict[str, dict]:
    by_prefix = {d.content_hash[:12]: by_id[d.id] for d in docs if d.content_hash}
    return {
        k: by_prefix[m.group(0)]
        for k in keys
        if (m := _HASH_PREFIX_RE.match(k)) and m.group(0) in by_prefix
    }


def _issue_from_reason(
    reason: dict, severity: str, by_key: dict[str, dict], by_id: dict[str, dict]
) -> dict:
    key = reason.get("artifact_key") or ""
    identity = by_id.get(reason.get("document_id") or "") or by_key.get(key)
    context = {
        "artifact_key": key,
        "document_id": reason.get("document_id"),
        "offending_value": reason.get("offending_value"),
        "expected": reason.get("expected"),
    }
    if identity:
        context.update(identity)
    return {
        "code": reason.get("code", ""),
        "severity": severity,
        "path": None,
        "context": context,
        "legacy_message": reason.get("message", ""),
    }


def _sentinel_issue(code: str, severity: str, remaining: int) -> dict:
    return {
        "code": code,
        "severity": severity,
        "path": None,
        "context": {"truncated": True, "remaining": remaining},
        "legacy_message": f"e mais {remaining} ocorrencia(s) de {code}",
    }


def _issues_for_code(code, group, severity, by_key, by_id) -> list[dict]:
    """Top-N do grupo + sentinela ``truncated`` quando estoura o cap."""
    issues = [_issue_from_reason(r, severity, by_key, by_id) for r in group[:_ISSUE_CAP_PER_CODE]]
    if len(group) > _ISSUE_CAP_PER_CODE:
        issues.append(_sentinel_issue(code, severity, len(group) - _ISSUE_CAP_PER_CODE))
    return issues


def _issues_from_reasons(
    reasons: list[dict], by_key: dict[str, dict], by_id: dict[str, dict]
) -> list[dict]:
    """Projeção ReviewReason → ValidationIssue (ADR-272 crit. 6 · ADR-308 §3):
    cap top-N por code + sentinela ``truncated``; total exato vive na tabela."""
    from pipeline.domain.review_reason import BLOCKING_CODES

    blocking = {c.value for c in BLOCKING_CODES}
    by_code: dict[str, list[dict]] = {}
    for reason in reasons:
        by_code.setdefault(reason.get("code", ""), []).append(reason)
    ordered = sorted(by_code.items(), key=lambda i: (0 if i[0] in blocking else 1, -len(i[1])))
    issues: list[dict] = []
    for code, group in ordered:
        severity = "error" if code in blocking else "warning"
        issues.extend(_issues_for_code(code, group, severity, by_key, by_id))
    return issues


def _record_stage_needs_review(
    run_id: str,
    stage_name: str,
    log_id: str,
    result,
    elapsed_ms: int,
) -> None:
    validation = result.detail.get("validation", {}) if result.detail else {}
    legacy_text = "\n".join(validation.get("errors", []))
    structured_issues = validation.get("issues") or None  # ADR-165 onda 2
    review_reasons = validation.get("review_reasons") or []  # ADR-272 Fase 2

    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if not structured_issues and review_reasons:
            by_key, by_id = _resolve_document_identities(db, run.workspace_id, review_reasons)
            structured_issues = _issues_from_reasons(review_reasons, by_key, by_id)
        stage_log = db.get(PipelineStageLog, log_id)
        stage_log.status = PipelineStageStatus.needs_review
        stage_log.duration_ms = elapsed_ms
        stage_log.completed_at = datetime.now(timezone.utc)
        stage_log.output_summary = result.detail
        db.add(
            StageReview(
                pipeline_run_id=run_id,
                stage=stage_name,
                status=StageReviewStatus.pending,
                original_output_json=result.detail,
                validation_errors=legacy_text,
                validation_issues=structured_issues,
            )
        )
        run.status = PipelineRunStatus.needs_review
        run.paused_at_stage = stage_name
        run.current_stage = None
        inserted = _materialize_review_reasons(
            db,
            run_id=run_id,
            workspace_id=run.workspace_id,
            stage_name=stage_name,
            reasons=review_reasons,
        )
        db.commit()
    if review_reasons:
        logger.info(
            "review_reasons materializadas: run=%s stage=%s rows=%d entries=%d",
            run_id,
            stage_name,
            inserted,
            len(review_reasons),
        )
    publish_needs_review(run_id, stage_name)


_PARECER_STAGE_NAME = "review_finances_holistic"


# `success` e `status == "needs_review"` saíram do filtro (ADR-366 · A40.l20 PR2):
# o desfecho retido é EXATAMENTE `success: False` + `status: "needs_review"`, e
# recusá-lo aqui é o que tornava o membro `retido` inalcançável. Discriminar
# retenção-com-motivo de indisponibilidade técnica NÃO se duplica aqui — é
# `_is_persistable` no domínio quem decide, com `retention_reason` (ADR-366 §D6).
#
# `persona_hash` continua fechando a rota de exceção: SystemExit/Exception no
# runner produzem `detail=_with_tail(None)`, sem nenhum campo de auditoria, e a
# persistência os indexa em colunas NOT NULL.
def _should_persist_planner_review(stage_name: str, result) -> bool:
    """Filtro: stage do parecer com detail de geração — entregue OU retido."""
    if stage_name != _PARECER_STAGE_NAME:
        return False
    if not isinstance(result.detail, dict):
        return False
    # `skipped` é ausência (free / sem chave / flag off / sem E5): nada foi gerado.
    if result.detail.get("skipped"):
        return False
    return "persona_hash" in result.detail


def _persist_planner_review_if_applicable(run_id: str, stage_name: str, result) -> None:
    """Wire-up ADR-199 / ADR-208 — materializa PlannerReview + cost + Suggestions."""
    if not _should_persist_planner_review(stage_name, result):
        return
    from backend.app.services.planner_review_persistence import (
        persist_after_stage_result,
    )

    with SyncSessionLocal() as db:
        persist_after_stage_result(db, run_id=run_id, detail=result.detail)


def _summarize_per_doc_errors(detail) -> str | None:
    """Sumariza ``detail.errors[]`` (contrato soft-fail dos stages — extract_comprovantes_bens, extract_invoices/E2-llm, generate_narratives/E5.N) para ``stage_log.errors``. Sem isso, UI mostra só fallback genérico."""
    if not isinstance(detail, dict):
        return None
    per_doc = detail.get("errors") or []
    if not per_doc:
        return None
    lines: list[str] = []
    for entry in per_doc:
        if isinstance(entry, dict):
            lines.append(f"{entry.get('file', '?')}: {entry.get('error', '')}")
        else:
            lines.append(str(entry))
    return "\n".join(lines)[:2000] or None


# `cost_usd` e `cost_known` viajam JUNTOS. `LLMService.call` só registra a chamada
# DEPOIS de `create()` retornar, então falha pós-cobrança dá `cost_known=False` —
# logar `cost_usd: 0.0` sozinho reportaria "grátis" exatamente no timeout caro.
# `None` faz agregação falhar alto em vez de enviesar para baixo; `0.0` com
# `cost_known=True` é fato (stage sem LLM).
def _cost_pair(detail) -> tuple[float | None, bool]:
    metrics = detail.get("llm_metrics") if isinstance(detail, dict) else None
    metrics = metrics if isinstance(metrics, dict) else {}
    return metrics.get("cost_usd"), bool(metrics.get("cost_known", False))


def _log_stage_degraded(
    run_id: str, stage_name: str, reason: str, detail, *, criticality: str
) -> None:
    """`WARNING` (anomalia recuperável — o run entregou), namespace `mathoms.*`."""
    cost_usd, cost_known = _cost_pair(detail)
    logger.warning(
        "stage_degraded",
        extra={
            "event": "mathoms.pipeline.stage_degraded",
            "run_id": run_id,
            "stage": stage_name,
            "criticality": criticality,
            "reason_class": reason,
            "cost_usd": cost_usd,
            "cost_known": cost_known,
        },
    )


def _summary_with_reason(detail, reason: str) -> dict:
    """Merge sobre CÓPIA — `output_summary` é atribuição TOTAL nos caminhos terminais."""
    # Mutar `result.detail` in-place não é rastreado pelo tipo `JSON` do
    # SQLAlchemy (coluna sem `MutableDict`), e sobrescrever o summary inteiro
    # apaga o detail do stage. Precedente: `summary["redelivered"]`.
    summary = dict(detail) if isinstance(detail, dict) else {}
    summary["reason_class"] = reason
    return summary


def _record_stage_result(
    run_id: str,
    stage_name: str,
    log_id: str,
    result,
    elapsed_ms: int,
    completed_pct: int,
    outcome: "StageOutcome",
    reason_class: str = "unknown",
) -> bool:
    """Persiste resultado final do stage + publica evento. Retorna ``True`` se ENTREGOU. Pós-stage hook ADR-199 materializa ``PlannerReview`` se ``stage_name == review_finances_holistic``."""
    with SyncSessionLocal() as db:
        stage_log = db.get(PipelineStageLog, log_id)
        stage_log.status = _STAGE_STATUS_BY_OUTCOME[outcome]
        stage_log.duration_ms = elapsed_ms
        stage_log.completed_at = datetime.now(timezone.utc)
        stage_log.output_summary = (
            result.detail
            if outcome.delivered
            else _summary_with_reason(result.detail, reason_class)
        )
        if result.error:
            stage_log.errors = result.error
        elif not outcome.delivered:
            stage_log.errors = _summarize_per_doc_errors(result.detail)
        db.commit()

    # FORA do ramo `delivered` (ADR-366 §Alternativas rejeitadas): o desfecho do
    # parecer é eixo próprio e NÃO deriva do status do stage. Um parecer retido
    # devolve `success: False`, o registry declara o stage `degradable`, e
    # `StageOutcome.degraded.delivered` é False — era esta linha, não o filtro
    # abaixo, que mantinha o membro `retido` inalcançável em produção. O artifact
    # já está commitado neste ponto (`commit_artifacts_on_degrade`, ADR-357 §6).
    _persist_planner_review_if_applicable(run_id, stage_name, result)

    if outcome.delivered:
        publish_stage_completed(run_id, stage_name, completed_pct)
        return True

    publish_stage_failed(run_id, stage_name, result.error or "Unknown error", completed_pct)
    # ADR-357 §3 — `failed_at_stage` NÃO é populado em degradação: preenchido ao
    # lado de um status entregue, ele mentiria para todo leitor futuro (e o
    # `deriveFailedStage` do frontend pintaria a etapa de vermelho num run que
    # entregou). O stage degradado é derivável de `stage_logs`.
    if outcome == "failed":
        with SyncSessionLocal() as db:
            run = db.get(PipelineRun, run_id)
            run.failed_at_stage = stage_name
            db.commit()
    return False


def _has_validation_errors(result) -> bool:
    return bool(
        result.detail
        and isinstance(result.detail, dict)
        and isinstance(result.detail.get("validation"), dict)
        and not result.detail["validation"].get("valid", True)
    )


def _execute_stages_loop(
    ctx,
    stages: list[str],
    run_id: str,
    ws_id: str,
    skip_llm: bool,
    stop_on_error: bool,
    tier: str,
    llm_stages,
    run_stage_fn,
    base_run_id: str | None = None,
    base_run_fallback_stages: frozenset[str] = frozenset(),
) -> tuple[bool, bool]:
    """Executa o loop principal de stages.

    Abre uma sessão fresca + ``DBArtifactStore`` por stage e fecha após
    commit/rollback — libera o write-lock SQLite entre stages, evitando
    contenção com a sessão que escreve em ``pipeline_stage_logs``
    (ADR-212 PR3a: sempre ``DBArtifactStore``; flag dies).

    Retorna ``(has_failure, paused_for_review)``. Degradação NÃO entra na tupla:
    é propriedade do run e o finalize a lê de ``stage_logs`` (ADR-357 §3) — flag
    local mediria só esta invocação, e resume/redelivery partem o run em duas.
    """
    from backend.app.services.pipeline import stage_failure_reason as sfr
    from pipeline.stage_outcome import (
        commits_artifacts_on_degrade,
        resolve_stage_outcome,
        stage_criticality,
    )

    has_failure = False
    paused_for_review = False
    total_stages = len(stages)

    for stage_idx, stage_name in enumerate(stages):
        if _is_cancelled(run_id):
            publish_run_cancelled(run_id)
            break

        # A37.l12 (EXEC-01): redelivery com stage já concluído neste run →
        # pula reusando os artefatos (zero call LLM nova, sem row duplicada).
        marker = _find_stage_completion_marker(run_id, stage_name)
        if marker is not None:
            _record_stage_redelivery_skip(
                run_id, stage_name, marker, int(((stage_idx + 1) / total_stages) * 100)
            )
            continue

        is_llm = stage_name in llm_stages
        should_skip_llm = skip_llm and is_llm
        should_skip_free = tier == "free" and is_llm and not skip_llm

        log_id = str(uuid.uuid4())
        stage_started_at = datetime.now(timezone.utc)
        progress_pct = int((stage_idx / total_stages) * 100)

        if should_skip_llm or should_skip_free:
            _record_stage_skip(
                run_id,
                stage_name,
                log_id,
                stage_started_at,
                should_skip_free,
                progress_pct,
            )
            continue

        _record_stage_running(run_id, stage_name, log_id, stage_started_at, progress_pct)

        # Sessão por-stage (libera write-lock entre stages).
        stage_session, store = _open_artifact_session(
            ws_id, run_id, base_run_id, base_run_fallback_stages
        )
        ctx.artifact_store = store

        start_mono = time.monotonic()
        result, attempts, exc_error, exc_tb, exc_reason = _run_stage_with_retry(
            ctx, stage_name, run_stage_fn
        )
        elapsed_ms = int((time.monotonic() - start_mono) * 1000)
        completed_pct = int(((stage_idx + 1) / total_stages) * 100)

        # Exception during stage (all retries exhausted): rollback + close.
        if result is None:
            outcome = resolve_stage_outcome(stage_name, delivered=False)
            _rollback_and_close_artifact_session(stage_session)
            _record_stage_exception(
                run_id,
                stage_name,
                log_id,
                attempts,
                exc_error,
                exc_tb,
                elapsed_ms,
                progress_pct,
                outcome,
                exc_reason,
            )
            if outcome == "degraded":
                _log_stage_degraded(
                    run_id, stage_name, exc_reason, None, criticality=stage_criticality(stage_name)
                )
                continue
            has_failure = True
            if stop_on_error:
                break
            continue

        # A28.l8: needs_review deixa de ser exclusivo de stage LLM — E3
        # determinístico emite validation.valid=False para período implausível
        # / banco vazio (review_reasons ADR-272). Stages sem bloco validation
        # seguem intocados (_has_validation_errors default valid=True).
        if result.success and _has_validation_errors(result):
            # needs_review: commit artefatos coletados antes de pausar.
            try:
                _commit_and_close_artifact_session(stage_session)
            except Exception:  # noqa: BLE001
                logger.exception("artifact commit failed on needs_review stage=%s", stage_name)
            _record_stage_needs_review(run_id, stage_name, log_id, result, elapsed_ms)
            paused_for_review = True
            break

        outcome = resolve_stage_outcome(
            stage_name,
            delivered=bool(result.success),
            declared_skip=isinstance(result.detail, dict) and bool(result.detail.get("skipped")),
        )
        reason = (
            sfr.StageFailureReason.unknown.value
            if outcome.delivered
            else sfr.reason_from_stage_detail(result.detail).value
        )

        if result.success:
            try:
                _commit_and_close_artifact_session(stage_session)
            except Exception as exc:  # noqa: BLE001
                logger.exception("artifact commit failed stage=%s: %s", stage_name, exc)
                has_failure = True
                _record_stage_result(
                    run_id, stage_name, log_id, result, elapsed_ms, completed_pct, outcome, reason
                )
                if stop_on_error:
                    break
                continue
        elif outcome == "degraded" and commits_artifacts_on_degrade(stage_name):
            # ADR-357 §6 — artifact degradado é COMMITADO (nunca publicado): a
            # superfície de diagnóstico precisa ter o que ler, e o marcador
            # terminal promete "artefatos persistidos". A exceção travada é o
            # stage que escreve em chave de OUTRO stage (`generate_narratives`
            # grava na chave do E5): ali não há onde pôr o marcador
            # `_meta.status` que os dois leitores usam para discriminar, e
            # commitar mentiria sobre um E5 que está completo.
            try:
                _commit_and_close_artifact_session(stage_session)
            except Exception as exc:  # noqa: BLE001
                logger.exception("artifact commit failed on degrade stage=%s: %s", stage_name, exc)
        else:
            _rollback_and_close_artifact_session(stage_session)

        delivered = _record_stage_result(
            run_id,
            stage_name,
            log_id,
            result,
            elapsed_ms,
            completed_pct,
            outcome,
            reason,
        )
        if outcome == "degraded":
            _log_stage_degraded(
                run_id, stage_name, reason, result.detail, criticality=stage_criticality(stage_name)
            )
        # Degradação NUNCA honra `stop_on_error`. Os 3 degradáveis são os 3
        # últimos de FULL_ORDER, nesta ordem, e o default do trigger/resume é
        # `True`: parar aqui faria degradar `generate_narratives` apagar também
        # `validate_cross` e o parecer que o cliente premium pagou — uma lacuna
        # virando três, criada pela própria lane que existe para matá-las.
        if not delivered and outcome == "failed":
            has_failure = True
            if stop_on_error:
                break

    return has_failure, paused_for_review


# Desfechos em que o post-processing roda — quem cria a row em `reports`,
# materializa lineage edges e sincroniza status E2 (ADR-357 §5 · ADR-131).
#
# Predicado POSITIVO de propósito. O antigo `if not has_failure` era negativo, e
# negativo deixa passar todo status futuro sem decisão. `partial_failure` entra
# porque o entregável existe — é o ponto inteiro da lane.
#
# `cancelled` entra para PRESERVAR comportamento vivo: hoje o loop faz `break`
# com `has_failure=False`, `_finalize_run` early-returna no status e o gate
# antigo ficava verdadeiro. Cancelar depois de `analyze_finances` já gera
# relatório. Mudar isso é decisão de produto e lane própria — não desta.
_POST_PROCESS_STATUSES = (
    PipelineRunStatus.completed,
    PipelineRunStatus.partial_failure,
    PipelineRunStatus.cancelled,
)


def _degraded_stages(db, run_id: str) -> list[str]:
    """Stages com ``stage_log`` degradado neste run."""
    # Consultado no DB, não herdado de flag do loop: a degradação é propriedade do
    # RUN, e a flag local mede a INVOCAÇÃO. O `resume` re-despacha a task com o
    # mesmo `run_id` e só os stages restantes (caminho vivo, não exótico), e o
    # redelivery pula stages já concluídos pelo marcador — nos dois casos as
    # flags voltam limpas e o run finalizaria `completed` com um stage degradado
    # no banco.
    from sqlalchemy import select

    return list(
        db.execute(
            select(PipelineStageLog.stage).where(
                PipelineStageLog.pipeline_run_id == run_id,
                PipelineStageLog.status == PipelineStageStatus.degraded,
            )
        )
        .scalars()
        .all()
    )


# ADR-291: run só-de-cauda (`from_stage`) lê o E5 do run BASE por fallback do
# store, então o predicado de entregável não pode filtrar só por
# `pipeline_run_id == run.id` — reprovaria um run de cauda que está íntegro.
def _run_has_deliverable(db, run: PipelineRun) -> bool:
    """Existe artifact E5 alcançável por este run — inclui o base run de ``from_stage``."""
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from pipeline.artifact_store import stage_aliases
    from pipeline.domain.services.e5_serialization import E5_ARTIFACT_KEY, E5_OUTPUT_STAGE

    run_ids = [r for r in (run.id, run.base_run_id) if r]
    row = db.execute(
        select(PipelineArtifact.id).where(
            PipelineArtifact.pipeline_run_id.in_(run_ids),
            PipelineArtifact.stage.in_(stage_aliases(E5_OUTPUT_STAGE)),
            PipelineArtifact.artifact_key == E5_ARTIFACT_KEY,
        )
    ).first()
    return row is not None


def _terminal_status(db, run: PipelineRun, *, has_failure: bool) -> PipelineRunStatus:
    """Desfecho 3-way do run (ADR-357 §3/§5)."""
    if has_failure:
        return PipelineRunStatus.failed
    if not _degraded_stages(db, run.id):
        return PipelineRunStatus.completed
    # A cegueira da §2 é sobre a FORMA da não-entrega do STAGE. "O run entregou?"
    # é pergunta de run, respondida por evidência — sem E5 não há relatório, e
    # `partial_failure` ("entregue com lacuna declarada") mentiria.
    if _run_has_deliverable(db, run):
        return PipelineRunStatus.partial_failure
    return PipelineRunStatus.failed


def _finalize_run(run_id: str, has_failure: bool) -> PipelineRunStatus:
    """Seta o desfecho terminal do ``PipelineRun``, publica evento e o retorna."""
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        if run.status in (PipelineRunStatus.cancelled, PipelineRunStatus.needs_review):
            return run.status
        status = _terminal_status(db, run, has_failure=has_failure)
        run.status = status
        run.completed_at = datetime.now(timezone.utc)
        run.current_stage = None
        db.commit()
    if status is PipelineRunStatus.failed:
        publish_run_failed(run_id)
    else:
        publish_run_completed(run_id, status=status.value)
    return status


def _materialize_lineage_edges(ws_id: str, run_id: str) -> None:
    """Hook pós-run do índice reverso (ADR-279 · A25.l3) — DELETE+INSERT atômico no writer."""
    from backend.app.services.lineage_edge_writer import materialize_lineage_edges

    with SyncSessionLocal() as db:
        materialize_lineage_edges(db, workspace_id=ws_id, run_id=run_id)


def _parecer_meta_for_run(db, ws_id: str, run_id: str) -> dict | None:
    from sqlalchemy import select

    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.services.security.crypto import read_artifact_content
    from pipeline.artifact_store import stage_aliases

    row = db.execute(
        select(PipelineArtifact.content_json).where(
            PipelineArtifact.workspace_id == ws_id,
            PipelineArtifact.pipeline_run_id == run_id,
            PipelineArtifact.stage.in_(stage_aliases("review_finances_holistic")),
            PipelineArtifact.artifact_key == "parecer_planejador",
        )
    ).first()
    if row is None or row[0] is None:
        return None
    return read_artifact_content(row[0]).get("_meta") or {}


def _published_parecer_entries(db, ws_id: str, run_id: str) -> list | None:
    """Âncoras verificadas do parecer PUBLICADO do run; None se ausente/needs_review."""
    meta = _parecer_meta_for_run(db, ws_id, run_id)
    if meta is None or meta.get("status") != "Gerado":
        return None
    return meta.get("evidencia_verification") or []


def _materialize_parecer_citation_edges(ws_id: str, run_id: str) -> None:
    """Hook pós-run das citações do parecer (ADR-293 slice 2, A27.l1) — só parecer
    publicado vira edge; âncora falhada nunca entra no grafo."""
    from backend.app.services.lineage_edge_writer import (
        e5_payload_for_run,
        materialize_parecer_citation_edges,
    )
    from backend.app.services.parecer_citation_lineage import build_parecer_citation_edges

    with SyncSessionLocal() as db:
        entries = _published_parecer_entries(db, ws_id, run_id)
        e5_data = e5_payload_for_run(db, ws_id, run_id) if entries is not None else None
        if entries is None or e5_data is None:
            return
        edges = build_parecer_citation_edges(e5_data, entries)
        materialize_parecer_citation_edges(db, workspace_id=ws_id, run_id=run_id, edges=edges)


def _run_post_processing(ws_id: str, run_id: str, tenant_root: Path) -> None:
    """Passos pós-sucesso: sync documents, gerar report, persistir sugestões.

    Cada passo é best-effort — falha só gera warning, não aborta o run.
    """
    import logging as _logging

    post_logger = _logging.getLogger("pipeline_task.post")

    try:
        from backend.app.services.pipeline.document_pipeline_sync import (
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
        post_logger.warning("Failed to sync document E2 status: %s", exc)

    try:
        _create_report_from_output(ws_id, run_id, tenant_root)
    except Exception:
        # Loga traceback completo: bug silencioso aqui (warning sem stack)
        # mascarou a regressão A6c+ADR-129 por ~12h em prod.
        post_logger.exception("report_creation_failed for ws=%s run=%s", ws_id, run_id)

    # ADR-279 / A25.l3: materializa o índice reverso artifact_lineage_edge
    # (retenção N=1 por workspace). Best-effort: tabela derivada/rebuildável —
    # falha nunca aborta o run; run falho não chega aqui (edges do último run
    # bem-sucedido permanecem).
    try:
        _materialize_lineage_edges(ws_id, run_id)
    except Exception as exc:
        post_logger.warning("Failed to materialize lineage edges: %s", exc)

    # ADR-293 / A27.l1 slice 2: citação verificada do parecer vira edge de
    # lineage (E6→E5) por chave natural. Mesmo regime best-effort acima.
    try:
        _materialize_parecer_citation_edges(ws_id, run_id)
    except Exception as exc:
        post_logger.warning("Failed to materialize parecer citation edges: %s", exc)

    # ADR-259 §3 / A20.l15: CPF nunca sai do LLM — o valor é extraído do
    # documento original e cifrado aqui (só preenche cpf_encrypted NULL).
    try:
        from backend.app.services.family_member_pii_service import backfill_member_cpfs

        with SyncSessionLocal() as db:
            backfill_member_cpfs(db, workspace_id=ws_id, tenant_root=tenant_root, dry_run=False)
    except Exception as exc:
        post_logger.warning("Failed to backfill member CPFs: %s", exc)

    # ADR-074 / F8.4: persiste tarefas_sugeridas do E5.N no DB
    # (se existirem no JSON de análise).
    try:
        _persist_llm_suggestions(ws_id, run_id, tenant_root)
    except Exception as exc:
        post_logger.warning("Failed to persist LLM suggestions: %s", exc)

    # ADR-153 / Direção E · Onda 5: re-gera aggregate Suggestion a partir
    # do snapshot E5 do Report (idempotente). Sem isso, /acao Inbox e
    # SuggestionCallout no relatório ficam vazios após cada run.
    try:
        _persist_aggregate_suggestions(ws_id, run_id)
    except Exception as exc:
        post_logger.warning("Failed to persist aggregate suggestions: %s", exc)


def _close_artifact_session(artifact_session, run_id: str) -> None:
    """No-op de compat: sessão é agora por-stage e fechada no loop.

    Mantido para callers legados (ex.: caminho de abort em _mark_run_started).
    Se uma sessão ainda estiver viva por alguma razão, faz commit+close.
    """
    if artifact_session is None:
        return
    try:
        artifact_session.commit()
    except Exception:
        artifact_session.rollback()
    finally:
        artifact_session.close()
        logger.debug("artifact_session closed for run_id=%s", run_id)


def _finalize_pipeline_outcome(
    run_id: str,
    ws_id: str,
    tenant_root: Path,
    has_failure: bool,
    paused_for_review: bool,
) -> None:
    """Finaliza run + roda post-processing — extraído p/ achatar nesting (P9)."""
    if paused_for_review:
        return
    if _finalize_run(run_id, has_failure) in _POST_PROCESS_STATUSES:
        _run_post_processing(ws_id, run_id, tenant_root)


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
    base_run_id: str | None = None,
    base_run_fallback_stages: list[str] | None = None,
) -> dict:
    """Execute pipeline stages sequentially as a Celery task.

    Tier-aware:
    - free tier: LLM stages auto-skipped
    - premium: LLM stages run; validation failures → StageReview + pause
    """
    # A6f.1 · ADR-112 — pipeline execution goes through PipelineServiceClient
    # (InProcess default, Http when MATHOMS_PIPELINE_SERVICE_URL is set).
    # `_execute_stages_loop` keeps its shape; we derive llm_stages from
    # STAGE_REGISTRY and pass a closure binding workspace_id.
    _bootstrap_pipeline_sys_path()
    from backend.app.services.pipeline.pipeline_client import get_pipeline_client
    from pipeline.stage_spec import STAGE_REGISTRY

    pipeline_client = get_pipeline_client()
    llm_stages = {name for name, spec in STAGE_REGISTRY.items() if spec.is_llm}

    def _exec_stage(c, s):
        return pipeline_client.execute_stage(c, s, workspace_id=ws_id)

    tenant_root = Path(tenant_root_str)
    config_dir = Path(config_dir_str)

    ctx, config_store_session = _setup_run_context(
        run_id,
        ws_id,
        tenant_root,
        config_dir,
        incremental,
        incremental_doc_paths,
        skip_llm,
    )
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

    # C8/ADR-329 + A37.l3: run premium re-tenta docs parkados por skip transitório
    # antes das stages, reincorporando-os ao corpus. Só em run completo (não
    # incremental) — as stages leem data/ fresco; um doc roteado agora é lido.
    # A key do LLM é resolvida DENTRO do retry (llm_config DB-backed → env,
    # paridade com o parecer) — o gate env-only parkava docs p/ sempre em worker
    # sem a env var.
    if not incremental and not skip_llm:
        _retry_parked_documents(ws_id, tenant_root)

    # ADR-273: propaga contexto do run aos logs estruturados do pipeline.
    # Reset no finally é obrigatório — worker Celery reusa o processo e um
    # contextvar vazado carregaria workspace de outro tenant no próximo run.
    from backend.app.middleware.correlation import get_trace_id
    from pipeline.observability.context import bind as obs_bind
    from pipeline.observability.context import reset as obs_reset

    obs_tokens = obs_bind(trace_id=get_trace_id(), workspace_id=ws_id, run_id=run_id)
    try:
        # ADR-077 + ADR-180: configs DB-first vêm via ``ctx.config_overrides``
        # (montado por ``build_config_overrides_from_db``); apenas ``tarefas.md``
        # ainda é materializado em filesystem (texto livre fora do bundle tipado).
        _materialize_tarefas_md(ws_id, ctx)

        if not _mark_run_started(run_id, tier, self.request.id):
            return {"status": "error", "detail": "Run not found"}

        has_failure, paused_for_review = _execute_stages_loop(
            ctx,
            stages,
            run_id,
            ws_id,
            skip_llm,
            stop_on_error,
            tier,
            llm_stages,
            _exec_stage,
            base_run_id=base_run_id,
            base_run_fallback_stages=frozenset(base_run_fallback_stages or []),
        )

        _finalize_pipeline_outcome(run_id, ws_id, tenant_root, has_failure, paused_for_review)
        return {"status": "completed" if not has_failure else "failed", "run_id": run_id}
    finally:
        obs_reset(obs_tokens)
        _close_config_store_session(config_store_session)
