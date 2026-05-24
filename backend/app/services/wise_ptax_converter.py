"""WisePtaxConverter — busca PTAX 31/12 via MarketRateRepository (A17 L3 P3 · ADR-238 D5 · ADR-135)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from backend.app.repositories.market_rate_repository import MarketRateRepository


class WisePtaxConverter:
    """Adapter raise→None sobre `MarketRateRepository` (ADR-135): merger precisa fallback graceful."""

    def __init__(self, repo: MarketRateRepository) -> None:
        self._repo = repo

    def get_rate_or_none(self, moeda: str, ano_base: int) -> Optional[Decimal]:
        """Cotação PTAX `MOEDA/BRL` em 31/12/`ano_base` (ou anterior mais próximo)."""
        if moeda == "BRL":
            return Decimal("1")
        observed_at = date(ano_base, 12, 31)
        row = self._repo.get_latest_on_or_before(f"{moeda}/BRL", observed_at)
        return row.rate if row is not None else None
