"""Adapter SQLAlchemy do `EconomicAssumptionsResolver` (ADR-219 wave 2)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.services.economic_assumptions_service import (
    EconomicAssumptionsService,
)
from backend.app.services.economic_assumptions_service import (
    ResolvedAssumption as ServiceResolvedAssumption,
)
from pipeline.domain.types.economic_assumption import ResolvedAssumption


class DBEconomicAssumptionsResolver:
    """Wrap `EconomicAssumptionsService` para o boundary do pipeline (ADR-219)."""

    def __init__(self, session: Session) -> None:
        self._service = EconomicAssumptionsService(session)

    def get_vigentes_em(
        self, as_of: date, workspace_id: Optional[str] = None
    ) -> tuple[ResolvedAssumption, ...]:
        """Delegar para service, mapeando o tipo backend → tipo domain."""
        rows = self._service.get_vigentes_em(as_of, workspace_id=workspace_id)
        return tuple(_to_domain(r) for r in rows)


def _to_domain(r: ServiceResolvedAssumption) -> ResolvedAssumption:
    return ResolvedAssumption(
        classe_auvp=r.classe_auvp,
        status=r.status,
        retorno_real_esperado_pct_anual=r.retorno_real_esperado_pct_anual,
        sigma_anual_pct=r.sigma_anual_pct,
        fonte=r.fonte,
        fonte_origem=r.fonte_origem,
        effective_from=r.effective_from,
        justificativa=r.justificativa,
        razao_indisponivel=r.razao_indisponivel,
    )
