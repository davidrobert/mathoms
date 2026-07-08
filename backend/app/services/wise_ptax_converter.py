"""WisePtaxConverter — busca PTAX 31/12 via MarketRateRepository (A17 L3 P3 · ADR-238 D5 · ADR-135).

Convenção (emenda ADR-135, 2026-07-07): ``market_rates.rate`` para pares
``*/BRL`` é PTAX de **compra** — mesma base da RFB para bens/direitos e do
GCAP. Lado venda exige schema evolution futura.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from backend.app.repositories.market_rate_repository import MarketRateRepository
from pipeline.domain.services.ptax_types import PtaxQuote

#: Guard anti-bootstrap: cotação aceita só se observada em dezembro do
#: ano-base. Rows de bootstrap (2024-01-01 com cotação de 2026, seed A7.2b)
#: retornariam valor patrimonial errado em silêncio — preferimos degradar
#: para None (merger emite PtaxMissingWarning).
_MES_JANELA_PTAX = 12


class WisePtaxConverter:
    """Adapter raise→None sobre `MarketRateRepository` (ADR-135): merger precisa fallback graceful."""

    def __init__(self, repo: MarketRateRepository) -> None:
        self._repo = repo

    # Retorna None quando a única row disponível é anterior a dezembro do
    # ano-base (bootstrap/stale) — nunca converte com cotação de outra época.
    def get_quote_or_none(self, moeda: str, ano_base: int) -> Optional[PtaxQuote]:
        """PTAX compra `MOEDA/BRL` de 31/12 do ano-base (aceita último dia útil de dezembro)."""
        if moeda == "BRL":
            return PtaxQuote(rate=Decimal("1"), observed_at=date(ano_base, 12, 31))
        row = self._repo.get_latest_on_or_before(f"{moeda}/BRL", date(ano_base, 12, 31))
        if row is None or not self._is_within_ptax_window(row.observed_at, ano_base):
            return None
        return PtaxQuote(rate=row.rate, observed_at=row.observed_at)

    def get_rate_or_none(self, moeda: str, ano_base: int) -> Optional[Decimal]:
        """Compat: apenas a taxa (mesmo guard de janela do ``get_quote_or_none``)."""
        quote = self.get_quote_or_none(moeda, ano_base)
        return quote.rate if quote is not None else None

    @staticmethod
    def _is_within_ptax_window(observed_at: date, ano_base: int) -> bool:
        return observed_at.year == ano_base and observed_at.month == _MES_JANELA_PTAX
