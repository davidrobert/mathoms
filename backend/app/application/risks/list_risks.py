"""Use case: lista Risks do workspace ordenados por (impact_level, probability)."""

from __future__ import annotations

from backend.app.application.risks._protocols import RiskRepositoryProtocol
from backend.app.schemas.dto.risk import (
    RiskListResponse,
    risk_to_response,
)


async def list_risks(
    workspace_id: str,
    *,
    repo: RiskRepositoryProtocol,
) -> RiskListResponse:
    risks = await repo.list_by_workspace(workspace_id)
    items = [risk_to_response(r) for r in risks]
    return RiskListResponse(risks=items, total=len(items))
