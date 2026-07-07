"""Tipos PTAX compartilhados entre merger/detectors e o adapter backend (ADR-135 · ADR-238)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Optional


@dataclass(frozen=True)
class PtaxQuote:
    """Cotação PTAX de **compra** `MOEDA/BRL` (convenção RFB p/ bens/direitos — emenda ADR-135)."""

    rate: Decimal
    observed_at: date


#: Função de cotação injetada no domínio: `(moeda, ano_base) → PtaxQuote | None`.
#: `None` = cotação 31/12 do ano-base indisponível (graceful degradation).
PtaxGetter = Callable[[str, int], Optional[PtaxQuote]]
