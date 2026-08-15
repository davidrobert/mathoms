"""``FiscalParameter`` — tabela GLOBAL versionada por vigência (ADR-135)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class FiscalParameter(Base):
    """Parâmetros fiscais BR (IRPF/PGBL/INSS) com vigência — tabela global (ADR-135)."""

    __tablename__ = "fiscal_parameters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # ADR-389 D2: a RFB publica DUAS tabelas — a mensal (IRRF na fonte) e a anual
    # (ajuste da DAA, Anexo VII da IN RFB 1.500/2014). Nenhuma deriva da outra:
    # em ano de transição a anual é mistura ponderada por mês, e mesmo em ano
    # limpo diverge por arredondamento. Cada uma carrega vigencia_ref + source.
    ir_brackets_anual: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ir_brackets_mensal: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # ADR-389 D4: o consumidor recusa lendo a row, não com `if year >= 2026`.
    regime_completo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    componentes_ausentes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Legado do seed A7.2b — escalas misturadas (tetos anuais, parcelas mensais).
    # Mantido nullable durante a janela expand/contract; leitores novos usam os
    # dois campos acima. Contract em lane própria.
    ir_brackets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    pgbl_limit_brl_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    inss_ceiling_brl_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lucro_presumido_aliquota: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
