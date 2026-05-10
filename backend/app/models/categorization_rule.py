"""``CategorizationRule`` — regra de categorização promovida (ADR-186 §D3 · A12 P1)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class CategorizationRule(Base):
    """Regra de categorização promovida de override (ADR-186 §D3)."""

    __tablename__ = "categorization_rules"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "keyword",
            "target_category",
            name="uq_cat_rules_ws_keyword_target",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    target_category: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100"
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    # Soft reference (sem FK formal) para ``transaction_overrides.id`` —
    # campo audit-only que sobrevive mesmo se o override original for
    # deletado. FK formal criaria ciclo com ``transaction_overrides.rule_id``
    # que SQLite/SQLAlchemy não conseguem ordenar em DROP. ADR-186 §D3 menciona
    # o FK; relaxado em P1 sem perda de funcionalidade (revert lookup usa
    # rule_id na direção oposta).
    origin_override_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    applied_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    revert_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
