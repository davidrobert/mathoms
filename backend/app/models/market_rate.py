"""``MarketRate`` — tabela GLOBAL de cotações observadas (ADR-135)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class MarketRate(Base):
    # Invariante (emenda ADR-135, 2026-07-07): `rate` para pares */BRL é PTAX
    # de COMPRA (convenção RFB p/ bens/direitos e GCAP). Lado venda exige
    # schema evolution futura — não reinterprete rows existentes; `source` é
    # reforço de auditoria apenas.
    """Cotação PTAX compra observada por par (USD/BRL, EUR/BRL, GBP/BRL) — tabela global (ADR-135)."""

    __tablename__ = "market_rates"
    __table_args__ = (
        UniqueConstraint("pair", "observed_at", name="uq_market_rates_pair_observed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pair: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    observed_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # ADR-239 D7 (A18 L3 — FIPE refresh): mês de referência da cotação ('YYYY-MM').
    # FIPE publica tabelas mensais; capturar permite reconciliar cotação histórica
    # com mês de referência declarado no informe. Nullable porque câmbio PTAX
    # diário (USD/BRL) não usa.
    reference_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
