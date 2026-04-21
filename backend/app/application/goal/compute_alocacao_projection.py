"""Use case: dry-run da alocação-alvo (valida soma == 100%)."""

from __future__ import annotations

from backend.app.schemas.dto.goal import (
    AlocacaoGoalComputeRequest,
    AlocacaoGoalComputeResponse,
)
from backend.app.services.goal_service import compute_alocacao_derived


def compute_alocacao_projection(
    cmd: AlocacaoGoalComputeRequest,
) -> AlocacaoGoalComputeResponse:
    derived = compute_alocacao_derived(cmd.inputs)
    return AlocacaoGoalComputeResponse(
        derived=derived,
        valido=abs(derived.soma_percentuais - 100.0) < 0.01,
    )
