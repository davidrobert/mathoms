"""Cancela apólice (soft delete via ``status='Cancelada'``, ADR-192)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.app.application.base.errors import NotFoundError, PreconditionFailedError
from backend.app.application.protections._protocols import (
    ProtectionRepositoryProtocol,
)
from backend.app.models.protection import Protection
from backend.app.schemas.dto.protection import (
    ProtectionCancelCommand,
    ProtectionResponse,
    protection_to_response,
)

_logger = logging.getLogger("mathoms.protection")


def _append_reason(protection: Protection, reason: str | None) -> None:
    if reason:
        previous = protection.notes or ""
        protection.notes = f"{previous}\nCancelamento: {reason}".strip()


async def _fetch_or_raise(
    workspace_id: str, protection_id: str, repo: ProtectionRepositoryProtocol
) -> Protection:
    protection = await repo.get_by_id(workspace_id, protection_id)
    if protection is None:
        raise NotFoundError(
            f"Protection id={protection_id} não encontrada",
            code="protection_not_found",
        )
    if protection.status == "Cancelada":
        raise PreconditionFailedError("Protection já está Cancelada", code="already_cancelled")
    return protection


async def cancel_protection(
    cmd: ProtectionCancelCommand,
    *,
    workspace_id: str,
    protection_id: str,
    repo: ProtectionRepositoryProtocol,
) -> ProtectionResponse:
    protection = await _fetch_or_raise(workspace_id, protection_id, repo)
    protection.status = "Cancelada"
    _append_reason(protection, cmd.reason)
    protection.updated_at = datetime.now(timezone.utc)
    await repo.add(protection)
    _logger.info(
        "protection_cancelled",
        extra={
            "workspace_id": workspace_id,
            "protection_id": protection.id,
            "has_reason": cmd.reason is not None,
        },
    )
    return protection_to_response(protection)
