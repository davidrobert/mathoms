"""LGPD self-service endpoints — direitos do titular (Art. 18, V e VI)."""

# Soft-delete + grace 30d (ADR-072). `process_user_deletions` cron finaliza
# hard-delete. token_version++ força logout em todas as sessões. Export é
# assíncrono (Celery) e o download token é one-shot — file removido após
# servir. Antes deste módulo, o fluxo só existia via console interno.

from __future__ import annotations

import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models import (
    DataExportRequest,
    DataExportRequestStatus,
)
from backend.app.models.user import User
from backend.app.schemas.lgpd import (
    DataExportCreatedResponse,
    DataExportStatusResponse,
    DeletionCanceledResponse,
    DeletionRequestResponse,
)
from backend.app.services.audit import AuditAction, audit_log
from backend.app.services.lgpd_email import send_deletion_scheduled_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["me"])


DELETION_GRACE_DAYS = 30
ETA_MINUTES_DEFAULT = 5
EXPORT_REQUEST_COOLDOWN_HOURS = 1


def _as_utc(value: datetime | None) -> datetime | None:
    """SQLite read-back perde timezone; normalize para UTC antes de
    comparar com `now`."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _enqueue_export(request_id: str) -> None:
    """Hook overrideable em tests para evitar broker Redis. Em produção,
    delega para o worker Celery via `.delay()`."""
    from backend.app.tasks.lgpd_export import process_data_export

    process_data_export.delay(request_id)


def _build_status_response(
    req: DataExportRequest,
    *,
    include_url: bool = False,
) -> DataExportStatusResponse:
    download_url = None
    if include_url and req.status == DataExportRequestStatus.ready and req.download_token:
        download_url = f"/api/v1/me/data-export/{req.id}/download?token={req.download_token}"
    return DataExportStatusResponse(
        request_id=req.id,
        status=req.status,
        created_at=req.created_at,
        completed_at=req.completed_at,
        expires_at=req.expires_at,
        file_size_bytes=req.file_size_bytes,
        error_message=req.error_message,
        download_url=download_url,
    )


@router.post(
    "/data-export",
    response_model=DataExportCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_data_export(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataExportCreatedResponse:
    """LGPD Art. 18, V — solicita pacote portável dos dados do titular."""
    await _enforce_export_cooldown(db, user_id=current_user.id)
    req = DataExportRequest(
        user_id=current_user.id,
        status=DataExportRequestStatus.pending,
    )
    db.add(req)
    await db.flush()
    await audit_log(
        db,
        action=AuditAction.lgpd_export_requested,
        resource_type="data_export_request",
        resource_id=req.id,
        actor_user_id=current_user.id,
        request=request,
    )
    await db.commit()
    _enqueue_export(req.id)
    return DataExportCreatedResponse(
        request_id=req.id,
        status=req.status,
        eta_minutes=ETA_MINUTES_DEFAULT,
    )


async def _enforce_export_cooldown(db: AsyncSession, *, user_id: str) -> None:
    """Bloqueia novo request se há um em andamento ou ready recente."""
    in_flight = await db.execute(
        select(DataExportRequest).where(
            DataExportRequest.user_id == user_id,
            DataExportRequest.status.in_(
                [DataExportRequestStatus.pending, DataExportRequestStatus.processing]
            ),
        )
    )
    if in_flight.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "data_export_already_in_progress",
                "message": "Já existe uma solicitação em andamento. Aguarde a conclusão.",
            },
        )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=EXPORT_REQUEST_COOLDOWN_HOURS)
    recent_ready = await db.execute(
        select(DataExportRequest).where(
            DataExportRequest.user_id == user_id,
            DataExportRequest.status == DataExportRequestStatus.ready,
            DataExportRequest.created_at >= cutoff,
        )
    )
    if recent_ready.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "data_export_recent_ready",
                "message": "Existe um export recente pronto para download.",
            },
        )


@router.get("/data-export/{request_id}", response_model=DataExportStatusResponse)
async def get_data_export_status(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataExportStatusResponse:
    req = await _load_export(db, request_id=request_id, user_id=current_user.id)
    return _build_status_response(req, include_url=True)


@router.get("/data-export/{request_id}/download", response_class=FileResponse)
async def download_data_export(
    request_id: str,
    request: Request,
    token: str = Query(..., min_length=8),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """One-shot download. Marca `downloaded` e remove tar.gz após servir."""
    req = await _load_export(db, request_id=request_id, user_id=current_user.id)
    _validate_download_or_410(req, token=token)
    file_path = req.file_path  # type: ignore[assignment]
    req.status = DataExportRequestStatus.downloaded
    req.download_token = None
    req.completed_at = datetime.now(timezone.utc)
    await audit_log(
        db,
        action=AuditAction.lgpd_export_downloaded,
        resource_type="data_export_request",
        resource_id=req.id,
        actor_user_id=current_user.id,
        request=request,
    )
    await db.commit()
    return FileResponse(
        path=file_path,
        media_type="application/gzip",
        filename=f"mathoms-export-{req.id}.tar.gz",
        background=BackgroundTask(_unlink_after_serve, file_path),
    )


def _validate_download_or_410(req: DataExportRequest, *, token: str) -> None:
    if req.status != DataExportRequestStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "code": "data_export_not_ready",
                "message": f"Export não disponível (status={req.status}).",
            },
        )
    expires_at = _as_utc(req.expires_at)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "data_export_expired", "message": "Link de download expirado."},
        )
    if not req.download_token or not hmac.compare_digest(req.download_token, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "invalid_token", "message": "Token inválido."},
        )
    if not req.file_path or not Path(req.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "code": "data_export_file_missing",
                "message": "Arquivo do export não encontrado.",
            },
        )


def _unlink_after_serve(file_path: str) -> None:
    try:
        os.unlink(file_path)
    except OSError:
        logger.warning("download_data_export.unlink_failed path=%s", file_path)


@router.post(
    "/delete-request",
    response_model=DeletionRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_account_deletion(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeletionRequestResponse:
    """LGPD Art. 18, VI — soft-delete + grace 30d, bumps token_version."""
    if current_user.deletion_requested_at is not None:
        return _idempotent_deletion_response(current_user)
    now = datetime.now(timezone.utc)
    current_user.deletion_requested_at = now
    current_user.token_version = current_user.token_version + 1
    await audit_log(
        db,
        action=AuditAction.lgpd_deletion_requested,
        resource_type="user",
        resource_id=current_user.id,
        actor_user_id=current_user.id,
        request=request,
        details={"grace_days": DELETION_GRACE_DAYS},
    )
    await db.commit()
    hard_delete_after = now + timedelta(days=DELETION_GRACE_DAYS)
    send_deletion_scheduled_email(
        to_email=current_user.email,
        hard_delete_after_iso=hard_delete_after.isoformat(),
    )
    return DeletionRequestResponse(
        user_id=current_user.id,
        deletion_requested_at=now,
        hard_delete_after=hard_delete_after,
        message=(
            f"Sua conta será removida em {DELETION_GRACE_DAYS} dias. Para cancelar, "
            "faça login e use DELETE /api/v1/me/delete-request dentro deste prazo."
        ),
    )


def _idempotent_deletion_response(user: User) -> DeletionRequestResponse:
    assert user.deletion_requested_at is not None
    return DeletionRequestResponse(
        user_id=user.id,
        deletion_requested_at=user.deletion_requested_at,
        hard_delete_after=user.deletion_requested_at + timedelta(days=DELETION_GRACE_DAYS),
        message="Solicitação de exclusão já estava registrada.",
    )


@router.delete("/delete-request", response_model=DeletionCanceledResponse)
async def cancel_account_deletion(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeletionCanceledResponse:
    if current_user.deletion_requested_at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "no_pending_deletion",
                "message": "Nenhuma solicitação de exclusão pendente.",
            },
        )
    current_user.deletion_requested_at = None
    await audit_log(
        db,
        action=AuditAction.lgpd_deletion_canceled,
        resource_type="user",
        resource_id=current_user.id,
        actor_user_id=current_user.id,
        request=request,
    )
    await db.commit()
    return DeletionCanceledResponse(
        user_id=current_user.id,
        message="Solicitação de exclusão cancelada.",
    )


async def _load_export(db: AsyncSession, *, request_id: str, user_id: str) -> DataExportRequest:
    row = await db.execute(
        select(DataExportRequest).where(
            DataExportRequest.id == request_id,
            DataExportRequest.user_id == user_id,
        )
    )
    req = row.scalar_one_or_none()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "data_export_not_found", "message": "Request inexistente."},
        )
    return req
