"""Use cases: vincula/desvincula apólice como mitigação de um Risk (ADR-192)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.app.application.base.errors import (
    ConflictError,
    NotFoundError,
)
from backend.app.application.protections._protocols import (
    ProtectionRepositoryProtocol,
)
from backend.app.application.risks._protocols import RiskRepositoryProtocol
from backend.app.schemas.dto.protection import (
    ProtectionLinkToRiskCommand,
    ProtectionResponse,
    protection_to_response,
)

_logger = logging.getLogger("mathoms.protection")


async def _fetch_protection_and_risk(
    workspace_id: str,
    protection_id: str,
    risk_id: str,
    *,
    repo: ProtectionRepositoryProtocol,
    risk_repo: RiskRepositoryProtocol,
):
    protection = await repo.get_by_id(workspace_id, protection_id)
    if protection is None:
        raise NotFoundError(
            f"Protection id={protection_id} não encontrada",
            code="protection_not_found",
        )
    risk = await risk_repo.get_by_id(workspace_id, risk_id)
    if risk is None:
        raise NotFoundError(f"Risk id={risk_id} não encontrado", code="risk_not_found")
    return protection, risk


async def _persist_risk_mitigations(risk, new_ids: list[str], risk_repo) -> None:
    risk.mitigation_protection_ids = new_ids if new_ids else None
    risk.updated_at = datetime.now(timezone.utc)
    await risk_repo.add(risk)


def _log_link_event(event: str, workspace_id: str, protection_id: str, risk_id: str) -> None:
    _logger.info(
        event,
        extra={
            "workspace_id": workspace_id,
            "protection_id": protection_id,
            "risk_id": risk_id,
        },
    )


async def link_to_risk(
    cmd: ProtectionLinkToRiskCommand,
    *,
    workspace_id: str,
    protection_id: str,
    repo: ProtectionRepositoryProtocol,
    risk_repo: RiskRepositoryProtocol,
) -> ProtectionResponse:
    protection, risk = await _fetch_protection_and_risk(
        workspace_id, protection_id, cmd.risk_id, repo=repo, risk_repo=risk_repo
    )
    current = list(risk.mitigation_protection_ids or [])
    if protection_id in current:
        raise ConflictError(
            "Protection já vinculada como mitigação deste Risk",
            code="duplicate_link",
        )
    current.append(protection_id)
    await _persist_risk_mitigations(risk, current, risk_repo)
    _log_link_event("protection_linked_to_risk", workspace_id, protection_id, cmd.risk_id)
    return protection_to_response(protection)


async def unlink_from_risk(
    *,
    workspace_id: str,
    protection_id: str,
    risk_id: str,
    repo: ProtectionRepositoryProtocol,
    risk_repo: RiskRepositoryProtocol,
) -> ProtectionResponse:
    protection, risk = await _fetch_protection_and_risk(
        workspace_id, protection_id, risk_id, repo=repo, risk_repo=risk_repo
    )
    current = list(risk.mitigation_protection_ids or [])
    if protection_id not in current:
        raise NotFoundError(
            "Protection não estava vinculada a este Risk",
            code="link_not_found",
        )
    current.remove(protection_id)
    await _persist_risk_mitigations(risk, current, risk_repo)
    _log_link_event("protection_unlinked_from_risk", workspace_id, protection_id, risk_id)
    return protection_to_response(protection)
