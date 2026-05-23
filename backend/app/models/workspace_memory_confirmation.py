"""Append-only confirmation log para campos derivados (ADR-262)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class WorkspaceMemoryConfirmation(Base):
    """Endosse de user para campo derivado de aggregate de leitura (ADR-262 Memories surface 3.E)."""

    __tablename__ = "workspace_memory_confirmations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_key: Mapped[str] = mapped_column(String(256), nullable=False)
    source_aggregate: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed_value_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workspace = relationship("Workspace")
    confirmer = relationship("User")

    __table_args__ = (
        Index("ix_wmc_ws_key", "workspace_id", "memory_key"),
        Index("ix_wmc_ws_confirmed_at", "workspace_id", "confirmed_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<WorkspaceMemoryConfirmation ws={self.workspace_id} "
            f"key={self.memory_key} at={self.confirmed_at}>"
        )
