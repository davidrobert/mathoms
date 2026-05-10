"""TransactionOverride — user corrections + ``source``/``rule_id`` (ADR-186 A12 P1)."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

OVERRIDE_SOURCE_MANUAL: str = "manual"
OVERRIDE_SOURCE_RULE: str = "rule"
VALID_OVERRIDE_SOURCES: frozenset[str] = frozenset({OVERRIDE_SOURCE_MANUAL, OVERRIDE_SOURCE_RULE})


class TransactionOverride(Base):
    __tablename__ = "transaction_overrides"
    __table_args__ = (
        UniqueConstraint("workspace_id", "transaction_hash", name="uq_override_ws_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_category: Mapped[str] = mapped_column(String(255), nullable=False)
    new_category: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OVERRIDE_SOURCE_MANUAL, server_default="manual"
    )
    rule_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("categorization_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspace = relationship("Workspace", back_populates="transaction_overrides")
