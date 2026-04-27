"""``FiscalParameter`` — tabela GLOBAL versionada por vigência (ADR-135)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, BigInteger, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class FiscalParameter(Base):
    """Parâmetros fiscais BR (IRPF/PGBL/INSS) com vigência — tabela global (ADR-135)."""

    __tablename__ = "fiscal_parameters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ir_brackets: Mapped[list] = mapped_column(JSON, nullable=False)
    pgbl_limit_brl_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    inss_ceiling_brl_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lucro_presumido_aliquota: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
