"""Use case: retorna uma Decision pelo id."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.decisions._protocols import DecisionRepositoryProtocol
from backend.app.schemas.dto.decision import DecisionResponse, decision_to_response


async def get_decision(
    workspace_id: str,
    decision_id: str,
    *,
    repo: DecisionRepositoryProtocol,
) -> DecisionResponse:
    decision = await repo.get_by_id(workspace_id, decision_id)
    if decision is None:
        raise NotFoundError(
            f"Decision id={decision_id} não encontrada no workspace",
            code="decision_not_found",
        )
    return decision_to_response(decision)
