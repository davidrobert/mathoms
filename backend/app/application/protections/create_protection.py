"""Use case: cria nova apólice (status default ``Ativa``)."""

from __future__ import annotations

import logging

from backend.app.application.base.errors import ValidationError
from backend.app.application.protections._protocols import (
    ProtectionRepositoryProtocol,
)
from backend.app.models.protection import Protection
from backend.app.schemas.dto.protection import (
    ProtectionCreateCommand,
    ProtectionResponse,
    brl_to_cents,
    protection_to_response,
)
from backend.app.services.protection_pii import encrypt_policy_ref, mask_coverage_bucket

_logger = logging.getLogger("mathoms.protection")


def _validate_create(cmd: ProtectionCreateCommand) -> int:
    if cmd.ends_at is not None and cmd.ends_at < cmd.starts_at:
        raise ValidationError("ends_at não pode ser anterior a starts_at", code="invalid_period")
    coverage_cents = brl_to_cents(cmd.coverage_brl)
    if coverage_cents is None or coverage_cents < 0:
        raise ValidationError("coverage_brl inválido", code="invalid_coverage")
    return coverage_cents


def _build_protection(
    cmd: ProtectionCreateCommand, *, workspace_id: str, coverage_cents: int
) -> Protection:
    return Protection(
        workspace_id=workspace_id,
        category=cmd.category,
        holder_family_member_id=cmd.holder_family_member_id,
        insurer=cmd.insurer,
        policy_ref=encrypt_policy_ref(cmd.policy_ref),
        coverage_brl_cents=coverage_cents,
        premium_monthly_brl_cents=brl_to_cents(cmd.premium_monthly_brl),
        coverage_type=cmd.coverage_type,
        starts_at=cmd.starts_at,
        ends_at=cmd.ends_at,
        status=cmd.status,
        notes=cmd.notes,
    )


async def create_protection(
    cmd: ProtectionCreateCommand,
    *,
    workspace_id: str,
    repo: ProtectionRepositoryProtocol,
) -> ProtectionResponse:
    coverage_cents = _validate_create(cmd)
    protection = _build_protection(cmd, workspace_id=workspace_id, coverage_cents=coverage_cents)
    added = await repo.add(protection)
    _logger.info(
        "protection_created",
        extra={
            "workspace_id": workspace_id,
            "protection_id": added.id,
            "category": added.category,
            "coverage_bucket": mask_coverage_bucket(added.coverage_brl_cents),
        },
    )
    return protection_to_response(added)
