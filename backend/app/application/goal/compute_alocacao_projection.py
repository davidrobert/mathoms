"""Use case: dry-run da alocação-alvo v2 (valida soma == 100%)."""

from __future__ import annotations

from backend.app.schemas.dto.goal import (
    AlocacaoGoalComputeRequest,
    AlocacaoGoalComputeResponse,
)
from backend.app.schemas.dto.goal.alocacao_shape_conversion import (
    compute_alocacao_derived_v2,
)


def compute_alocacao_projection(
    cmd: AlocacaoGoalComputeRequest,
) -> AlocacaoGoalComputeResponse:
    derived = compute_alocacao_derived_v2(cmd.inputs)
    return AlocacaoGoalComputeResponse(
        derived=derived,
        valido=abs(derived.soma_percentuais - 100.0) < 0.01,
    )
