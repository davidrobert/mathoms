"""TransactionOverride model — user corrections to auto-categorized transactions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspace = relationship("Workspace", back_populates="transaction_overrides")
