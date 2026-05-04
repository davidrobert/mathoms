"""Celery task — empacota dados LGPD e marca DataExportRequest ready/failed."""

# pending → processing → ready/failed. Idempotente: status != pending
# faz return early (Celery retry não duplica). Usa SyncSessionLocal
# (padrão worker), igual scan_all_deadlines.

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models import (
    DataExportRequest,
    DataExportRequestStatus,
    User,
)
from backend.app.services.audit import AuditAction, audit_log_sync
from backend.app.services.lgpd_email import send_export_ready_email
from backend.app.services.lgpd_export_service import (
    export_path_for,
    export_user_data,
)
from backend.app.worker import celery_app

logger = logging.getLogger(__name__)


_DOWNLOAD_TTL_DAYS = 7


def _build_download_url(request_id: str, token: str) -> str:
    return f"/api/v1/me/data-export/{request_id}/download?token={token}"


@celery_app.task(name="fin.lgpd.process_data_export", bind=True, max_retries=2)
def process_data_export(self, request_id: str) -> dict[str, object]:
    """Pack the export pointed by ``request_id`` and mark it ready."""
    with SyncSessionLocal() as db:
        req = db.execute(
            select(DataExportRequest).where(DataExportRequest.id == request_id)
        ).scalar_one_or_none()
        if req is None:
            logger.warning("lgpd_export.task.not_found request_id=%s", request_id)
            return {"status": "not_found", "request_id": request_id}
        if req.status != DataExportRequestStatus.pending:
            logger.info("lgpd_export.task.skip request_id=%s status=%s", request_id, req.status)
            return {"status": "skipped", "request_id": request_id, "current": req.status}
        user = db.execute(select(User).where(User.id == req.user_id)).scalar_one_or_none()
        if user is None:
            return _mark_failed_user_not_found(db, req)
        req.status = DataExportRequestStatus.processing
        db.commit()
        output_path = export_path_for(req.id)
        try:
            size = export_user_data(db, user_id=req.user_id, output_path=output_path)
        except Exception as exc:  # noqa: BLE001
            _mark_failed(db, req, exc)
            raise self.retry(exc=exc, countdown=60) from exc
        token = _mark_ready(db, req, output_path=output_path, size=size)
        send_export_ready_email(
            to_email=user.email,
            request_id=req.id,
            download_url=_build_download_url(req.id, token),
        )
        return {"status": "ready", "request_id": req.id, "size_bytes": size}


def _mark_failed_user_not_found(db, req: DataExportRequest) -> dict[str, object]:
    req.status = DataExportRequestStatus.failed
    req.error_message = "user_not_found"
    req.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "failed", "reason": "user_not_found"}


def _mark_failed(db, req: DataExportRequest, exc: Exception) -> None:
    logger.exception("lgpd_export.task.failed request_id=%s", req.id)
    req.status = DataExportRequestStatus.failed
    req.error_message = f"{type(exc).__name__}: {exc}"[:512]
    req.completed_at = datetime.now(timezone.utc)
    audit_log_sync(
        db,
        action=AuditAction.lgpd_export_failed,
        resource_type="data_export_request",
        resource_id=req.id,
        actor_user_id=req.user_id,
        details={"error": req.error_message},
    )
    db.commit()


def _mark_ready(db, req: DataExportRequest, *, output_path, size: int) -> str:
    token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    req.status = DataExportRequestStatus.ready
    req.download_token = token
    req.expires_at = now + timedelta(days=_DOWNLOAD_TTL_DAYS)
    req.file_path = str(output_path)
    req.file_size_bytes = size
    req.completed_at = now
    audit_log_sync(
        db,
        action=AuditAction.lgpd_export_ready,
        resource_type="data_export_request",
        resource_id=req.id,
        actor_user_id=req.user_id,
        details={"size_bytes": size, "expires_at": req.expires_at.isoformat()},
    )
    db.commit()
    return token
