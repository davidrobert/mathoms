"""Use case: histórico de versões da meta IF com autores."""

from __future__ import annotations

from typing import Mapping, Optional

from backend.app.application.goal._protocols import GoalRepositoryProtocol
from backend.app.schemas.dto.goal import IFGoalHistoryResponse, goal_to_if_response


async def list_if_goal_versions(
    workspace_id: str,
    *,
    repo: GoalRepositoryProtocol,
    author_names: Optional[Mapping[str, str]] = None,
) -> IFGoalHistoryResponse:
    """``author_names`` (user_id → nome) é pré-computado pelo router.

    Mantém o use case isento do ``User`` repo — cross-aggregate fica no
    boundary HTTP.
    """
    goals = await repo.list_by_workspace_and_type(
        workspace_id, "INDEPENDENCIA_FINANCEIRA"
    )
    lookup = dict(author_names or {})
    responses = [
        goal_to_if_response(g, created_by_name=lookup.get(g.created_by or ""))
        for g in goals
    ]
    return IFGoalHistoryResponse(goals=responses, total=len(responses))
