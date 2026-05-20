"""Tarefas periódicas Celery Beat — ADR-074 §F8.4 + LGPD self-service + ADR-172."""

# scan_all_deadlines (notifications), expire_data_exports (LGPD ttl janitor),
# process_user_deletions (LGPD hard-delete pós-grace 30d), detect_stuck_runs
# (ADR-172 W2-T04 — heartbeat timeout). Beat schedule em
# worker.py:celery_app.conf.beat_schedule.

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.core.database import SyncSessionLocal
from backend.app.models import (
    DataExportRequest,
    DataExportRequestStatus,
    Notification,
    User,
    Workspace,
)
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.audit import AuditAction, audit_log_sync
from backend.app.services.events import publish_run_failed
from backend.app.services.pipeline_failure_reasons import HEARTBEAT_TIMEOUT
from backend.app.services.task_notification_service import (
    scan_and_create_notifications,
)
from backend.app.worker import celery_app

logger = logging.getLogger(__name__)

DELETION_GRACE_DAYS = 30

#: ADR-172 — threshold após o qual um run ``running`` sem heartbeat é
#: considerado travado. Worst-case detection: ``beat_freq + threshold``.
DEFAULT_STUCK_RUN_THRESHOLD_MINUTES = 15


@celery_app.task(name="fin.scan_all_deadlines", bind=True, max_retries=1)
def scan_all_deadlines(self) -> dict[str, int]:
    """Varre TODOS os workspaces e dispara `scan_and_create_notifications`
    para cada um. Idempotente (dedup por title no notification).

    Retorna contadores agregados:
        {"workspaces_scanned": N, "total_created": M, "total_skipped": S}
    """
    import asyncio

    total_created = 0
    total_skipped = 0
    ws_count = 0

    # sync session — beat tasks rodam fora do event loop async
    with SyncSessionLocal() as db:
        # tenancy: global — admin job que varre todos os workspaces
        ws_ids = [row[0] for row in db.execute(select(Workspace.id)).fetchall()]

    for ws_id in ws_ids:
        try:
            stats = asyncio.run(_scan_one(ws_id))
            total_created += stats.get("created", 0)
            total_skipped += stats.get("skipped_existing", 0)
            ws_count += 1
        except Exception as exc:  # noqa: BLE001 — best-effort per workspace
            logger.warning(
                "scan_all_deadlines: workspace %s falhou: %s",
                ws_id,
                exc,
            )

    result = {
        "workspaces_scanned": ws_count,
        "total_created": total_created,
        "total_skipped": total_skipped,
    }
    logger.info("scan_all_deadlines: %s", result)
    return result


async def _scan_one(workspace_id: str) -> dict[str, int]:
    """Wrapper async para rodar o service (que usa AsyncSession)."""
    from backend.app.core.database import async_session as AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        stats = await scan_and_create_notifications(workspace_id, db=db)
        await db.commit()
    return stats


def _expire_one(db: Session, req: DataExportRequest, *, now: datetime) -> None:
    if req.file_path:
        try:
            os.unlink(req.file_path)
        except FileNotFoundError:
            pass
        except OSError as exc:  # noqa: BLE001 — log and proceed; status flip matters more
            logger.warning("expire_data_exports.unlink_failed path=%s err=%s", req.file_path, exc)
    req.status = DataExportRequestStatus.expired
    req.download_token = None
    req.completed_at = now
    audit_log_sync(
        db,
        action=AuditAction.lgpd_export_expired,
        resource_type="data_export_request",
        resource_id=req.id,
        actor_user_id=req.user_id,
        details={"expired_at": now.isoformat()},
    )


@celery_app.task(name="fin.lgpd.expire_data_exports", bind=True, max_retries=1)
def expire_data_exports(self) -> dict[str, int]:
    """Move ready requests com prazo vencido para `expired` e apaga arquivo."""
    now = datetime.now(timezone.utc)
    expired = 0
    with SyncSessionLocal() as db:
        rows = (
            db.execute(
                select(DataExportRequest).where(
                    DataExportRequest.status == DataExportRequestStatus.ready,
                    DataExportRequest.expires_at.is_not(None),
                    DataExportRequest.expires_at < now,
                )
            )
            .scalars()
            .all()
        )
        for req in rows:
            _expire_one(db, req, now=now)
            expired += 1
        db.commit()
    result = {"expired": expired, "checked_at": int(now.timestamp())}
    logger.info("expire_data_exports: %s", result)
    return result


def _hard_delete_user(db: Session, user: User, *, now: datetime) -> None:
    """Apaga User + cascade. AuditLog mantido com actor_user_id NULL (anonimizado)."""
    audit_log_sync(
        db,
        action=AuditAction.lgpd_deletion_completed,
        resource_type="user",
        resource_id=user.id,
        actor_user_id=None,
        details={
            "user_email_hash": _hash_email(user.email),
            "deletion_requested_at": (
                user.deletion_requested_at.isoformat() if user.deletion_requested_at else None
            ),
            "completed_at": now.isoformat(),
        },
    )
    db.delete(user)


def _hash_email(email: str) -> str:
    """SHA-256 hex truncado — registro auditável sem armazenar PII em claro."""
    import hashlib

    return hashlib.sha256(email.lower().encode("utf-8")).hexdigest()[:16]


@celery_app.task(name="fin.lgpd.process_user_deletions", bind=True, max_retries=1)
def process_user_deletions(self) -> dict[str, int]:
    """Hard-delete users cujo grace de 30 dias venceu."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=DELETION_GRACE_DAYS)
    deleted = 0
    with SyncSessionLocal() as db:
        rows = (
            db.execute(
                select(User).where(
                    User.deletion_requested_at.is_not(None),
                    User.deletion_requested_at < cutoff,
                )
            )
            .scalars()
            .all()
        )
        for user in rows:
            try:
                _hard_delete_user(db, user, now=now)
                deleted += 1
            except Exception as exc:  # noqa: BLE001 — best-effort per user
                logger.warning(
                    "process_user_deletions.failed user_id=%s err=%s",
                    user.id,
                    exc,
                )
                db.rollback()
                continue
        db.commit()
    result = {"hard_deleted": deleted, "cutoff": cutoff.isoformat()}
    logger.info("process_user_deletions: %s", result)
    return result


def _resolve_stuck_run_threshold() -> timedelta:
    raw = os.environ.get("MATHOMS_STUCK_RUN_THRESHOLD_MINUTES")
    try:
        minutes = int(raw) if raw else DEFAULT_STUCK_RUN_THRESHOLD_MINUTES
    except ValueError:
        minutes = DEFAULT_STUCK_RUN_THRESHOLD_MINUTES
    if minutes < 1:
        minutes = DEFAULT_STUCK_RUN_THRESHOLD_MINUTES
    return timedelta(minutes=minutes)


def _flip_stuck_run_atomic(db: Session, run: PipelineRun, *, now: datetime) -> bool:
    """UPDATE atômico filtrando ``status='running'`` — evita race com stage completion."""
    result = db.execute(
        update(PipelineRun)
        .where(PipelineRun.id == run.id, PipelineRun.status == PipelineRunStatus.running)
        .values(
            status=PipelineRunStatus.failed,
            failure_reason=HEARTBEAT_TIMEOUT,
            failed_at_stage=run.current_stage,
            completed_at=now,
            current_stage=None,
        )
    )
    return result.rowcount == 1


def _select_stuck_candidates(db: Session, cutoff: datetime) -> list[PipelineRun]:
    return list(
        db.execute(
            select(PipelineRun).where(
                PipelineRun.status == PipelineRunStatus.running,
                PipelineRun.last_heartbeat_at.is_not(None),
                PipelineRun.last_heartbeat_at < cutoff,
            )
        )
        .scalars()
        .all()
    )


def _stuck_run_notification(run: PipelineRun, stage: str | None) -> Notification:
    return Notification(
        workspace_id=run.workspace_id,
        severity="error",
        title="Processamento interrompido",
        message=(
            f"O processamento travou no estágio {stage or 'inicial'}. "
            "Clique em Reprocessar para retomar."
        ),
        source="pipeline",
    )


def _log_stuck_run(
    run: PipelineRun, *, stage: str | None, stale_minutes: float, threshold: timedelta
) -> None:
    logger.warning(
        "Stuck pipeline run detected",
        extra={
            "event": "mathoms.pipeline.stuck_run_detected",
            "run_id": run.id,
            "workspace_id": run.workspace_id,
            "stage": stage,
            "stale_minutes": round(stale_minutes, 1),
            "threshold_minutes": int(threshold.total_seconds() // 60),
        },
    )


def _flip_one_stuck(
    db: Session, run: PipelineRun, *, now: datetime, threshold: timedelta
) -> tuple[str, str] | None:
    stale_minutes = (now - run.last_heartbeat_at).total_seconds() / 60
    stage = run.current_stage
    if not _flip_stuck_run_atomic(db, run, now=now):
        return None
    db.add(_stuck_run_notification(run, stage))
    _log_stuck_run(run, stage=stage, stale_minutes=stale_minutes, threshold=threshold)
    return run.id, run.workspace_id


def _publish_failed_safe(run_id: str) -> None:
    try:
        publish_run_failed(run_id)
    except Exception as exc:  # noqa: BLE001 — best-effort WS publish
        logger.warning("detect_stuck_runs.publish_failed run=%s err=%s", run_id, exc)


@celery_app.task(name="fin.detect_stuck_runs", bind=True, max_retries=1)
def detect_stuck_runs(self) -> dict[str, int]:
    """ADR-172 (W2-T04) — flippa runs ``running`` com heartbeat estale para ``failed``."""
    threshold = _resolve_stuck_run_threshold()
    now = datetime.now(timezone.utc)
    detected: list[tuple[str, str]] = []
    with SyncSessionLocal() as db:
        for run in _select_stuck_candidates(db, now - threshold):
            flipped = _flip_one_stuck(db, run, now=now, threshold=threshold)
            if flipped:
                detected.append(flipped)
        db.commit()
    for run_id, _ws_id in detected:
        _publish_failed_safe(run_id)
    result = {"detected": len(detected)}
    logger.info("detect_stuck_runs: %s", result)
    return result
