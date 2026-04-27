"""``MarketRate`` — tabela GLOBAL de cotações observadas (ADR-135)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class MarketRate(Base):
    """Cotação observada de um par de moedas (USD/BRL, EUR/BRL, …).

    Tabela **global**. Lookup: última row em ``observed_at <= ?`` por par.
    ``UNIQUE(pair, observed_at)`` evita duplicatas para a mesma data.
    Câmbio é "última cotação conhecida na data ou antes" (ADR-135).
    """

    __tablename__ = "market_rates"
    __table_args__ = (
        UniqueConstraint("pair", "observed_at", name="uq_market_rates_pair_observed_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pair: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    observed_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
