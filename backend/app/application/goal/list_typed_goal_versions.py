"""Use case: histórico tipado de versões (aporte/dólar/alocação)."""

from __future__ import annotations

from typing import Mapping, Optional

from backend.app.application.goal._protocols import GoalRepositoryProtocol
from backend.app.schemas.dto.goal import GoalResponseBase, goal_to_typed_response


async def list_typed_goal_versions(
    workspace_id: str,
    goal_type: str,
    *,
    repo: GoalRepositoryProtocol,
    author_names: Optional[Mapping[str, str]] = None,
) -> list[GoalResponseBase]:
    goals = await repo.list_by_workspace_and_type(workspace_id, goal_type)
    lookup = dict(author_names or {})
    return [
        goal_to_typed_response(g, created_by_name=lookup.get(g.created_by or "")) for g in goals
    ]
