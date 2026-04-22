"""FeatureFlag model — workspace-level boolean flags (ADR-074).

Armazenado como única linha por workspace com um JSON dict de
{flag_name: bool}. Defaults em código (`feature_flags_service.DEFAULTS`).

Vantagens vs. reusar PipelineConfig:
- Semântica clara (não mistura com config operacional do pipeline).
- Unique por workspace_id → evita rows duplicadas.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flags_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workspace = relationship("Workspace")

    __table_args__ = (UniqueConstraint("workspace_id", name="uq_feature_flags_workspace"),)
