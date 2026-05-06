"""StageReview model — tracks LLM stages that need manual review after validation failures."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class StageReviewStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    edited = "edited"


class StageReview(Base):
    __tablename__ = "stage_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(StageReviewStatus), nullable=False, default=StageReviewStatus.pending
    )
    original_output_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    edited_output_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    validation_errors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # ADR-165 onda 2: lista de ValidationIssue serializada (code/severity/path/context/legacy_message).
    # NULL para reviews pré-cutover — UI faz fallback para `validation_errors`.
    validation_issues: Mapped[Optional[list[dict]]] = mapped_column(JSON, nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    pipeline_run = relationship("PipelineRun", back_populates="stage_reviews")
