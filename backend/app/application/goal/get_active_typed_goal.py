"""Use case: retorna meta vigente tipada (aporte, dólar, alocação)."""

from __future__ import annotations

from typing import Optional

from backend.app.application.base.errors import NotFoundError
from backend.app.application.goal._protocols import GoalRepositoryProtocol
from backend.app.schemas.dto.goal import GoalResponseBase, goal_to_typed_response


_NOT_FOUND_MESSAGES = {
    "APORTE_MENSAL": "Workspace ainda não tem meta de aportes configurada",
    "DOLARIZACAO": "Workspace ainda não tem meta de dolarização configurada",
    "ALOCACAO_ALVO": "Workspace ainda não tem alocação-alvo configurada",
}


async def get_active_typed_goal(
    workspace_id: str,
    goal_type: str,
    *,
    repo: GoalRepositoryProtocol,
    created_by_name: Optional[str] = None,
) -> GoalResponseBase:
    """404 se ``goal_type`` ainda não tem versão vigente no workspace."""
    goal = await repo.get_active_by_type(workspace_id, goal_type)
    if goal is None:
        msg = _NOT_FOUND_MESSAGES.get(
            goal_type, f"Workspace ainda não tem meta {goal_type}"
        )
        raise NotFoundError(msg, code="typed_goal_not_configured")
    return goal_to_typed_response(goal, created_by_name=created_by_name)
