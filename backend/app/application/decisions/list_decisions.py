"""Use case: lista todas as Decisions do workspace, ordenadas por ``code``."""

from __future__ import annotations

from backend.app.application.decisions._protocols import DecisionRepositoryProtocol
from backend.app.schemas.dto.decision import (
    DecisionListResponse,
    decision_to_response,
)


async def list_decisions(
    workspace_id: str,
    *,
    repo: DecisionRepositoryProtocol,
) -> DecisionListResponse:
    decisions = await repo.list_by_workspace(workspace_id)
    items = [decision_to_response(d) for d in decisions]
    return DecisionListResponse(decisions=items, total=len(items))
