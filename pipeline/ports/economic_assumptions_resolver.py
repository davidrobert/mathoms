"""`EconomicAssumptionsResolver` — boundary read-only de premissas econômicas (ADR-219)."""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol, runtime_checkable

from pipeline.domain.types.economic_assumption import ResolvedAssumption


@runtime_checkable
class EconomicAssumptionsResolver(Protocol):
    """Boundary para premissas econômicas vigentes (ADR-219)."""

    def get_vigentes_em(
        self, as_of: date, workspace_id: Optional[str] = None
    ) -> tuple[ResolvedAssumption, ...]:
        # ADR-219: retorna 1 linha por classe AUVP ativa (override > global);
        # classe sem premissa → status="indisponivel".
        ...
