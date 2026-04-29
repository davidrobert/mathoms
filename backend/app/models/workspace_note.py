"""WorkspaceNotes — notas livres por workspace, multi-row, com pin (ADR-154, supersede ReportNotes ADR-123)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class WorkspaceNotes(Base):
    """Nota livre por workspace (ADR-154)."""

    __tablename__ = "workspace_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    author_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    author = relationship("User")

    __table_args__ = (
        Index(
            "ix_workspace_notes_ws_pinned_updated",
            "workspace_id",
            "pinned",
            "updated_at",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<WorkspaceNotes ws={self.workspace_id} pinned={self.pinned} len={len(self.content)}>"
        )
