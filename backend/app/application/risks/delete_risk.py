"""Use case: deleta um Risk do workspace."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.risks._protocols import RiskRepositoryProtocol


async def delete_risk(
    *,
    workspace_id: str,
    risk_id: str,
    repo: RiskRepositoryProtocol,
) -> None:
    risk = await repo.get_by_id(workspace_id, risk_id)
    if risk is None:
        raise NotFoundError(f"Risk id={risk_id} não encontrado", code="risk_not_found")
    await repo.delete(risk)
