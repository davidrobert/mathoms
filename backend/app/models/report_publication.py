"""ReportPublication model — ADR-186 (mês fechado imutável)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class ReportPublication(Base):
    """Publicação de relatório (mês fechado) — ADR-186."""

    __tablename__ = "report_publications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_yyyymm: Mapped[str] = mapped_column(String(6), nullable=False)
    artifact_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pipeline_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_by: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    unpublished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workspace = relationship("Workspace")
    artifact = relationship("PipelineArtifact")

    __table_args__ = (
        CheckConstraint(
            "length(period_yyyymm) = 6",
            name="ck_report_publications_period_len",
        ),
        Index("ix_report_publications_workspace_id", "workspace_id"),
        Index(
            "ix_report_publications_workspace_period",
            "workspace_id",
            "period_yyyymm",
        ),
        Index(
            "uq_report_publications_active",
            "workspace_id",
            "period_yyyymm",
            unique=True,
            sqlite_where=text("unpublished_at IS NULL"),
            postgresql_where=text("unpublished_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        live = "live" if self.unpublished_at is None else "revoked"
        return f"<ReportPublication ws={self.workspace_id} period={self.period_yyyymm} {live}>"
