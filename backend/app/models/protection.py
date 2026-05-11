"""Aggregate `Protection` workspace-scoped (ADR-192) — apólices contratadas."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

VALID_PROTECTION_CATEGORIES: frozenset[str] = frozenset(
    {"vida", "invalidez", "saude", "patrimonial", "rc_profissional", "sucessorio"}
)

VALID_PROTECTION_STATUSES: frozenset[str] = frozenset({"Ativa", "Suspensa", "Cancelada", "Vencida"})

VALID_PROTECTION_COVERAGE_TYPES: frozenset[str] = frozenset({"term", "whole", "universal"})


class Protection(Base):
    """Apólice contratada workspace-scoped (ADR-192)."""

    __tablename__ = "protections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    holder_family_member_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    insurer: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    policy_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coverage_brl_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    premium_monthly_brl_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    coverage_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    starts_at: Mapped[date] = mapped_column(Date, nullable=False)
    ends_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="Ativa")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workspace = relationship("Workspace")

    __table_args__ = (
        Index("ix_protections_ws_status", "workspace_id", "status"),
        Index("ix_protections_ws_category", "workspace_id", "category"),
        Index("ix_protections_ws_ends_at", "workspace_id", "ends_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Protection ws={self.workspace_id} category={self.category} status={self.status}>"
