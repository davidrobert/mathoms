"""Use case: atualiza apólice (patch parcial)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.protections._protocols import (
    ProtectionRepositoryProtocol,
)
from backend.app.models.protection import Protection
from backend.app.schemas.dto.protection import (
    ProtectionResponse,
    ProtectionUpdateCommand,
    brl_to_cents,
    protection_to_response,
)
from backend.app.services.protection_pii import encrypt_policy_ref

_logger = logging.getLogger("mathoms.protection")


async def update_protection(
    cmd: ProtectionUpdateCommand,
    *,
    workspace_id: str,
    protection_id: str,
    repo: ProtectionRepositoryProtocol,
) -> ProtectionResponse:
    protection = await repo.get_by_id(workspace_id, protection_id)
    if protection is None:
        raise NotFoundError(
            f"Protection id={protection_id} não encontrada",
            code="protection_not_found",
        )
    _apply_patch(protection, cmd)
    _ensure_period_valid(protection)
    protection.updated_at = datetime.now(timezone.utc)
    await repo.add(protection)
    _logger.info(
        "protection_updated",
        extra={"workspace_id": workspace_id, "protection_id": protection.id},
    )
    return protection_to_response(protection)


def _patch_money(protection: Protection, cmd: ProtectionUpdateCommand) -> None:
    if cmd.coverage_brl is not None:
        cents = brl_to_cents(cmd.coverage_brl)
        if cents is None or cents < 0:
            raise ValidationError("coverage_brl inválido", code="invalid_coverage")
        protection.coverage_brl_cents = cents
    if cmd.premium_monthly_brl is not None:
        protection.premium_monthly_brl_cents = brl_to_cents(cmd.premium_monthly_brl)


def _patch_scalars(protection: Protection, cmd: ProtectionUpdateCommand) -> None:
    if cmd.holder_family_member_id is not None:
        protection.holder_family_member_id = cmd.holder_family_member_id
    if cmd.insurer is not None:
        protection.insurer = cmd.insurer
    if cmd.policy_ref is not None:
        protection.policy_ref = encrypt_policy_ref(cmd.policy_ref)
    if cmd.coverage_type is not None:
        protection.coverage_type = cmd.coverage_type
    if cmd.starts_at is not None:
        protection.starts_at = cmd.starts_at
    if cmd.ends_at is not None:
        protection.ends_at = cmd.ends_at
    if cmd.notes is not None:
        protection.notes = cmd.notes


def _apply_patch(protection: Protection, cmd: ProtectionUpdateCommand) -> None:
    _patch_scalars(protection, cmd)
    _patch_money(protection, cmd)


def _ensure_period_valid(protection: Protection) -> None:
    if protection.ends_at is not None and protection.ends_at < protection.starts_at:
        raise ValidationError(
            "ends_at não pode ser anterior a starts_at",
            code="invalid_period",
        )
