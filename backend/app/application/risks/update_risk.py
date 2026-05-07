"""Use case: atualiza campos editoriais do Risk.

Patch parcial: somente campos ``not None`` no command alteram o aggregate.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.application.base.errors import NotFoundError
from backend.app.application.risks._protocols import RiskRepositoryProtocol
from backend.app.models.risk import Risk
from backend.app.schemas.dto.risk import (
    RiskResponse,
    RiskUpdateCommand,
    brl_to_cents,
    risk_to_response,
)


async def update_risk(
    cmd: RiskUpdateCommand,
    *,
    workspace_id: str,
    risk_id: str,
    repo: RiskRepositoryProtocol,
) -> RiskResponse:
    risk = await repo.get_by_id(workspace_id, risk_id)
    if risk is None:
        raise NotFoundError(f"Risk id={risk_id} não encontrado", code="risk_not_found")

    _apply_patch(risk, cmd)
    risk.updated_at = datetime.now(timezone.utc)
    await repo.add(risk)  # flush UPDATE
    return risk_to_response(risk)


def _apply_patch(risk: Risk, cmd: RiskUpdateCommand) -> None:
    if cmd.name is not None:
        risk.name = cmd.name
    if cmd.rationale is not None:
        risk.rationale = cmd.rationale
    if cmd.probability is not None:
        risk.probability = cmd.probability
    if cmd.impact_level is not None:
        risk.impact_level = cmd.impact_level
    if cmd.impact_brl is not None:
        risk.impact_brl_cents = brl_to_cents(cmd.impact_brl)
    if cmd.status is not None:
        risk.status = cmd.status
