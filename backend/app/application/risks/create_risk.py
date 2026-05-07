"""Use case: cria Risk novo (status default ``Ativo``)."""

from __future__ import annotations

from backend.app.application.base.errors import ConflictError
from backend.app.application.risks._protocols import RiskRepositoryProtocol
from backend.app.models.risk import Risk
from backend.app.schemas.dto.risk import (
    RiskCreateCommand,
    RiskResponse,
    brl_to_cents,
    risk_to_response,
)


async def create_risk(
    cmd: RiskCreateCommand,
    *,
    workspace_id: str,
    repo: RiskRepositoryProtocol,
) -> RiskResponse:
    """Cria Risk. Conflito se já existe ``code`` no workspace."""
    existing = await repo.get_by_code(workspace_id, cmd.code)
    if existing is not None:
        raise ConflictError(
            f"Risk com code={cmd.code!r} já existe no workspace",
            code="duplicate_code",
        )

    risk = Risk(
        workspace_id=workspace_id,
        code=cmd.code,
        name=cmd.name,
        rationale=cmd.rationale,
        probability=cmd.probability,
        impact_level=cmd.impact_level,
        impact_brl_cents=brl_to_cents(cmd.impact_brl),
        status=cmd.status,
        mitigations_decision_ids=list(cmd.mitigations_decision_ids),
    )
    added = await repo.add(risk)
    return risk_to_response(added)
