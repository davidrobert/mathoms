"""Use case: retorna meta IF vigente + enriquecimento com patrimônio atual."""

from __future__ import annotations

from typing import Optional

from backend.app.application.base.errors import NotFoundError
from backend.app.application.goal._protocols import GoalRepositoryProtocol
from backend.app.schemas.dto.goal import IFGoalResponse, goal_to_if_response
from backend.app.services.goal_service import compute_if_derived


async def get_active_if_goal(
    workspace_id: str,
    *,
    repo: GoalRepositoryProtocol,
    patrimonio_atual_brl: Optional[float] = None,
    created_by_name: Optional[str] = None,
) -> IFGoalResponse:
    """Retorna meta IF com ``derived`` recalculado usando patrimônio atual.

    ``patrimonio_atual_brl`` e ``created_by_name`` são injetados pelo
    router — use case não sabe onde vive ``Report`` nem ``User``.
    """
    goal = await repo.get_active_by_type(workspace_id, "INDEPENDENCIA_FINANCEIRA")
    if goal is None:
        raise NotFoundError(
            "Workspace ainda não tem meta IF configurada",
            code="if_goal_not_configured",
        )
    base = goal_to_if_response(goal, created_by_name=created_by_name)
    return base.model_copy(
        update={"derived": compute_if_derived(base.inputs, patrimonio_atual_brl)}
    )
