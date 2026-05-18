"""Tipos de premissa econômica resolvida (ADR-219)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

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
