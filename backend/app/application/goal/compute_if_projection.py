"""Use case: dry-run da meta IF (sem persistência).

Enriquece ``derived`` com ``percentual_conquistado`` + ``faltante_brl``
quando ``patrimonio_atual_brl`` é informado.
"""

from __future__ import annotations

from decimal import Decimal

from backend.app.schemas.dto.goal import IFGoalComputeRequest, IFGoalComputeResponse
from backend.app.services.goal_service import compute_if_derived

_CENT = Decimal("0.01")
_ZERO = Decimal("0")


def compute_if_projection(cmd: IFGoalComputeRequest) -> IFGoalComputeResponse:
    """Preview live sem side-effects — função síncrona pura."""
    derived = compute_if_derived(cmd.inputs, cmd.patrimonio_atual_brl)

    pct = None
    falt = None
    if cmd.patrimonio_atual_brl is not None and derived.if_meta_brl > _ZERO:
        pct = float(
            (Decimal("100") * cmd.patrimonio_atual_brl / derived.if_meta_brl).quantize(_CENT)
        )
        falt = max(_ZERO, derived.if_meta_brl - cmd.patrimonio_atual_brl).quantize(_CENT)

    return IFGoalComputeResponse(
        derived=derived,
        percentual_conquistado=pct,
        faltante_brl=falt,
    )
