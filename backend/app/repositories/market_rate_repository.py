"""MarketRateRepository — leitura sync de cotações por par + data (ADR-135).

Lookup canônico: "última cotação conhecida em ``observed_at`` ou antes".

    SELECT * FROM market_rates
    WHERE pair = ? AND observed_at <= ?
    ORDER BY observed_at DESC LIMIT 1
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.market_rate import MarketRate


class MarketRateNotFound(RuntimeError):
    """Nenhuma cotação <= ``observed_at`` para o par."""


class MarketRateRepository:
    """Leitura sync de ``market_rates`` (consumido pelo worker)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_latest_on_or_before(self, pair: str, observed_at: date) -> MarketRate | None:
        """Última cotação de ``pair`` em data <= ``observed_at`` ou ``None``."""
        stmt = (
            select(MarketRate)
            .where(MarketRate.pair == pair)
            .where(MarketRate.observed_at <= observed_at)
            .order_by(MarketRate.observed_at.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalars().first()

    def get_rate(self, pair: str, observed_at: date) -> Decimal:
        """Helper que retorna apenas a taxa; raise se ausente."""
        row = self.get_latest_on_or_before(pair, observed_at)
        if row is None:
            raise MarketRateNotFound(
                f"No market_rates row found for pair={pair!r} on or before {observed_at}."
            )
        return row.rate

    def list_by_pair(self, pair: str) -> list[MarketRate]:
        """Histórico do par ordenado por ``observed_at`` desc."""
        stmt = (
            select(MarketRate)
            .where(MarketRate.pair == pair)
            .order_by(MarketRate.observed_at.desc())
        )
        return list(self._session.execute(stmt).scalars().all())
