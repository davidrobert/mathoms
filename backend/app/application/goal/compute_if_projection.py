"""Use case: dry-run da meta IF (sem persistência).

Enriquece ``derived`` com ``percentual_conquistado`` + ``faltante_brl``
quando ``patrimonio_atual_brl`` é informado.
"""

from __future__ import annotations

from backend.app.schemas.dto.goal import IFGoalComputeRequest, IFGoalComputeResponse
from backend.app.services.goal_service import compute_if_derived


def compute_if_projection(cmd: IFGoalComputeRequest) -> IFGoalComputeResponse:
    """Preview live sem side-effects — função síncrona pura."""
    derived = compute_if_derived(cmd.inputs, cmd.patrimonio_atual_brl)

    pct = None
    falt = None
    if cmd.patrimonio_atual_brl is not None and derived.if_meta_brl > 0:
        pct = round(100.0 * cmd.patrimonio_atual_brl / derived.if_meta_brl, 2)
        falt = round(max(0.0, derived.if_meta_brl - cmd.patrimonio_atual_brl), 2)

    return IFGoalComputeResponse(
        derived=derived,
        percentual_conquistado=pct,
        faltante_brl=falt,
    )
