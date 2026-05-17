"""Resolve premissas econômicas (ADR-219 D3) consolidando global + override."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy.orm import Session

from backend.app.repositories.economic_assumption_repository import (
    EconomicAssumptionRepository,
)

ResolvedFonte = Literal["global", "workspace_override"]
ResolvedStatus = Literal["emitted", "indisponivel"]


@dataclass(frozen=True)
class ResolvedAssumption:
    """Premissa econômica resolvida (global ou override) ou empty se indisponível."""

    classe_auvp: str
    status: ResolvedStatus
    retorno_real_esperado_pct_anual: Optional[Decimal] = None
    sigma_anual_pct: Optional[Decimal] = None
    fonte: Optional[str] = None
    fonte_origem: Optional[ResolvedFonte] = None
    effective_from: Optional[date] = None
    justificativa: Optional[str] = None
    razao_indisponivel: Optional[str] = None


def _index_by_classe(rows: list) -> dict:
    """Indexa rows por ``classe_auvp``; primeira ocorrência ganha (já vem ordenada desc)."""
    out: dict = {}
    for row in rows:
        out.setdefault(row.classe_auvp, row)
    return out


def _from_override(code: str, override) -> ResolvedAssumption:
    return ResolvedAssumption(
        classe_auvp=code,
        status="emitted",
        retorno_real_esperado_pct_anual=override.retorno_real_esperado_pct_anual,
        sigma_anual_pct=override.sigma_anual_pct,
        fonte=override.fonte,
        fonte_origem="workspace_override",
        effective_from=override.effective_from,
        justificativa=override.justificativa,
    )


def _from_global(code: str, global_row) -> ResolvedAssumption:
    return ResolvedAssumption(
        classe_auvp=code,
        status="emitted",
        retorno_real_esperado_pct_anual=global_row.retorno_real_esperado_pct_anual,
        sigma_anual_pct=global_row.sigma_anual_pct,
        fonte=global_row.fonte,
        fonte_origem="global",
        effective_from=global_row.effective_from,
    )


def _indisponivel(code: str, as_of: date) -> ResolvedAssumption:
    return ResolvedAssumption(
        classe_auvp=code,
        status="indisponivel",
        razao_indisponivel=(
            f"Sem premissa vigente em {as_of.isoformat()} (nem global, "
            "nem override do workspace)."
        ),
    )


class EconomicAssumptionsService:
    """Resolve premissas econômicas com override por workspace (ADR-219)."""

    def __init__(self, session: Session) -> None:
        self._repo = EconomicAssumptionRepository(session)

    def list_active_class_codes(self) -> list[str]:
        """Codes das classes AUVP ativas, ordenadas por ``sort_order``."""
        return [c.code for c in self._repo.list_active_classes()]

    def get_vigentes_em(
        self, as_of: date, workspace_id: Optional[str] = None
    ) -> tuple[ResolvedAssumption, ...]:
        """Resolve (global ∪ override) na data; override ganha; ausência → ``indisponivel``."""
        active_classes = self._repo.list_active_classes()
        if not active_classes:
            return ()
        global_by_classe = _index_by_classe(self._repo.list_global_vigentes_em(as_of))
        override_by_classe = (
            _index_by_classe(self._repo.list_workspace_overrides_vigentes_em(workspace_id, as_of))
            if workspace_id is not None
            else {}
        )
        return tuple(
            self._resolve_one(klass.code, as_of, global_by_classe, override_by_classe)
            for klass in active_classes
        )

    def _resolve_one(
        self,
        code: str,
        as_of: date,
        global_by_classe: dict,
        override_by_classe: dict,
    ) -> ResolvedAssumption:
        override = override_by_classe.get(code)
        if override is not None:
            return _from_override(code, override)
        global_row = global_by_classe.get(code)
        if global_row is not None:
            return _from_global(code, global_row)
        return _indisponivel(code, as_of)
