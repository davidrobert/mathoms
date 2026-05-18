"""Premissas econômicas auditáveis (ADR-219) — lookup AUVP + global versionada + override por workspace."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class EconomicAssetClass(Base):
    """Lookup de classes AUVP. Soft-deprecate via ``deprecated_at`` — ADR-219 D2."""

    __tablename__ = "economic_asset_class"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    deprecated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class EconomicAssumption(Base):
    """Premissa econômica global por classe AUVP, versionada por data (ADR-219 D1)."""

    __tablename__ = "economic_assumptions"
    __table_args__ = (
        UniqueConstraint(
            "classe_auvp", "effective_from", name="uq_economic_assumptions_classe_from"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    classe_auvp: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("economic_asset_class.code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    retorno_real_esperado_pct_anual: Mapped[Decimal] = mapped_column(
        Numeric(precision=6, scale=3), nullable=False
    )
    sigma_anual_pct: Mapped[Decimal] = mapped_column(Numeric(precision=6, scale=3), nullable=False)
    fonte: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class WorkspaceEconomicAssumptionOverride(Base):
    """Override por workspace. ``justificativa`` obrigatória (fiduciária) — ADR-219 D1."""

    __tablename__ = "workspace_economic_assumptions_override"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "classe_auvp",
            "effective_from",
            name="uq_ws_econ_override_ws_classe_from",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    classe_auvp: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("economic_asset_class.code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    retorno_real_esperado_pct_anual: Mapped[Decimal] = mapped_column(
        Numeric(precision=6, scale=3), nullable=False
    )
    sigma_anual_pct: Mapped[Decimal] = mapped_column(Numeric(precision=6, scale=3), nullable=False)
    fonte: Mapped[str] = mapped_column(Text, nullable=False)
    justificativa: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
