"""Use case: cria nova versão da meta IF (fecha vigente + insere)."""

from __future__ import annotations

from typing import Optional

from backend.app.application.goal._protocols import GoalRepositoryProtocol
from backend.app.schemas.dto.goal import (
    IFGoalResponse,
    IFGoalUpsertCommand,
    goal_to_if_response,
)
from backend.app.services.goal_service import compute_if_derived


async def create_if_goal_version(
    cmd: IFGoalUpsertCommand,
    *,
    workspace_id: str,
    created_by: Optional[str],
    repo: GoalRepositoryProtocol,
    patrimonio_atual_brl: Optional[float] = None,
    created_by_name: Optional[str] = None,
) -> IFGoalResponse:
    """Deriva via ``compute_if_derived`` e persiste append-only no repo.

    Retorna a resposta já enriquecida com patrimônio atual (mesmo flow
    de ``get_active_if_goal``).
    """
    derived = compute_if_derived(cmd.inputs)
    goal = await repo.create_new_version(
        workspace_id,
        "INDEPENDENCIA_FINANCEIRA",
        params_json={"inputs": cmd.inputs.model_dump(), "meta_version": 1},
        derived_json=derived.model_dump(exclude_none=True),
        created_by=created_by,
        notes=cmd.notes,
    )
    base = goal_to_if_response(goal, created_by_name=created_by_name)
    return base.model_copy(
        update={"derived": compute_if_derived(base.inputs, patrimonio_atual_brl)}
    )
