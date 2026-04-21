"""Use case: dry-run da meta de aportes."""

from __future__ import annotations

from backend.app.schemas.dto.goal import (
    AporteGoalComputeRequest,
    AporteGoalComputeResponse,
)
from backend.app.services.goal_service import compute_aporte_derived


def compute_aporte_projection(
    cmd: AporteGoalComputeRequest,
) -> AporteGoalComputeResponse:
    derived = compute_aporte_derived(cmd.inputs)
    return AporteGoalComputeResponse(derived=derived)
