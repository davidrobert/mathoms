"""Use case: dry-run da meta de dolarização (aplica câmbio default se omitido)."""

from __future__ import annotations

from backend.app.schemas.dto.goal import (
    DolarGoalComputeRequest,
    DolarGoalComputeResponse,
)
from backend.app.services.goal_service import (
    DEFAULT_CAMBIO_BRL_USD,
    compute_dolar_derived,
)


def compute_dolar_projection(
    cmd: DolarGoalComputeRequest,
) -> DolarGoalComputeResponse:
    cambio = cmd.cambio_brl_usd or DEFAULT_CAMBIO_BRL_USD
    derived = compute_dolar_derived(cmd.inputs, cambio)
    return DolarGoalComputeResponse(derived=derived, cambio_utilizado=cambio)
