"""Use case genérico: cria nova versão de aporte/dólar/alocação.

Dispatcha a compute function por ``goal_type``; caller passa inputs
tipados já validados pelo DTO.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from backend.app.application.base.errors import ValidationError
from backend.app.application.goal._protocols import GoalRepositoryProtocol
from backend.app.schemas.dto.goal import (
    AlocacaoGoalInputs,
    AporteGoalInputs,
    DolarGoalInputs,
    GoalResponseBase,
    goal_to_typed_response,
)
from backend.app.services.goal_service import (
    compute_alocacao_derived,
    compute_aporte_derived,
    compute_dolar_derived,
)


def _derive_for_type(goal_type: str, inputs: BaseModel) -> BaseModel:
    if goal_type == "APORTE_MENSAL" and isinstance(inputs, AporteGoalInputs):
        return compute_aporte_derived(inputs)
    if goal_type == "DOLARIZACAO" and isinstance(inputs, DolarGoalInputs):
        return compute_dolar_derived(inputs)
    if goal_type == "ALOCACAO_ALVO" and isinstance(inputs, AlocacaoGoalInputs):
        return compute_alocacao_derived(inputs)
    raise ValidationError(
        f"Goal type '{goal_type}' incompatível com inputs {type(inputs).__name__}",
        code="goal_type_inputs_mismatch",
    )


async def create_typed_goal_version(
    goal_type: str,
    inputs: BaseModel,
    notes: Optional[str],
    *,
    workspace_id: str,
    created_by: Optional[str],
    repo: GoalRepositoryProtocol,
    created_by_name: Optional[str] = None,
) -> GoalResponseBase:
    """Cria versão nova de aporte/dólar/alocação — dispatch interno por tipo."""
    derived = _derive_for_type(goal_type, inputs)
    goal = await repo.create_new_version(
        workspace_id,
        goal_type,
        params_json={"inputs": inputs.model_dump(mode="json"), "meta_version": 1},
        derived_json=derived.model_dump(mode="json", exclude_none=True),
        created_by=created_by,
        notes=notes,
    )
    return goal_to_typed_response(goal, created_by_name=created_by_name)
