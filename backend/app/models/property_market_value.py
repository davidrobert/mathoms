"""PropertyMarketValue — declaração versionada de valor de mercado (ADR-227 §D2)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

# Enum `source` (ADR-227 §D2). 3 fontes; V1 popula apenas `user_declared`.
# `avaliacao_terceiros` e `cep_proxy_futuro` reservados para V2.
PMV_SOURCE_USER_DECLARED = "user_declared"
PMV_SOURCE_AVALIACAO_TERCEIROS = "avaliacao_terceiros"
PMV_SOURCE_CEP_PROXY_FUTURO = "cep_proxy_futuro"

VALID_PMV_SOURCES = (
    PMV_SOURCE_USER_DECLARED,
    PMV_SOURCE_AVALIACAO_TERCEIROS,
    PMV_SOURCE_CEP_PROXY_FUTURO,
)


class PropertyMarketValue(Base):
    """Declaração versionada de valor de mercado (ADR-227 §D2) — append-only; correção é nova row + ``supersede()`` na antiga."""

    __tablename__ = "property_market_value"
    __table_args__ = (
        UniqueConstraint(
            "property_id",
            "valuation_date",
            name="uq_property_valuation_date",
        ),
        CheckConstraint(
            "source IN ('user_declared','avaliacao_terceiros','cep_proxy_futuro')",
            name="chk_pmv_source",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="chk_pmv_confidence",
        ),
        # Lookup index para latest_by_property (ADR-227 §D2):
        # DISTINCT ON (property_id) ORDER BY valuation_date DESC em
        # Postgres usa este índice composto para zero-sort lookup.
        Index(
            "idx_pmv_lookup",
            "workspace_id",
            "property_id",
            text("valuation_date DESC"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    property_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("property_identity.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    valor_brl_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    valuation_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    superseded_by_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("property_market_value.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


__all__ = [
    "PropertyMarketValue",
    "VALID_PMV_SOURCES",
    "PMV_SOURCE_USER_DECLARED",
    "PMV_SOURCE_AVALIACAO_TERCEIROS",
    "PMV_SOURCE_CEP_PROXY_FUTURO",
]
