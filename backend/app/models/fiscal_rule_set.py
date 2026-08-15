"""Rule-sets fiscais globais, tipados e versionados por vigência (ADR-387)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base

VALID_FISCAL_RULE_CODES = frozenset({"BR_ITCMD", "US_FBAR", "US_FATCA", "US_ESTATE_NRA"})


class FiscalRuleSet(Base):
    """Versão imutável de uma regra fiscal selecionável por data-base."""

    __tablename__ = "fiscal_rule_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_code: Mapped[str] = mapped_column(String(24), nullable=False)
    jurisdiction_code: Mapped[str] = mapped_column(String(24), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date)
    parameters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "rule_code IN ('BR_ITCMD','US_FBAR','US_FATCA','US_ESTATE_NRA')",
            name="chk_fiscal_rule_code",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_fiscal_rule_period",
        ),
        UniqueConstraint(
            "rule_code",
            "jurisdiction_code",
            "effective_from",
            name="uq_fiscal_rule_code_jurisdiction_from",
        ),
        Index("ix_fiscal_rule_lookup", "rule_code", "jurisdiction_code", "effective_from"),
    )


__all__ = ["FiscalRuleSet", "VALID_FISCAL_RULE_CODES"]
