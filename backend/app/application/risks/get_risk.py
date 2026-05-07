"""Use case: retorna um Risk pelo id."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.risks._protocols import RiskRepositoryProtocol
from backend.app.schemas.dto.risk import RiskResponse, risk_to_response


async def get_risk(
    workspace_id: str,
    risk_id: str,
    *,
    repo: RiskRepositoryProtocol,
) -> RiskResponse:
    risk = await repo.get_by_id(workspace_id, risk_id)
    if risk is None:
        raise NotFoundError(
            f"Risk id={risk_id} não encontrado no workspace",
            code="risk_not_found",
        )
    return risk_to_response(risk)
