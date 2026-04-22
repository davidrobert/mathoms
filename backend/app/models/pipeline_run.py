"""PipelineRun and PipelineStageLog models — execution tracking."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class PipelineRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    partial_failure = "partial_failure"
    failed = "failed"
    cancelled = "cancelled"
    needs_review = "needs_review"
    resuming = "resuming"


class PipelineStageStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"
    skipped_free_tier = "skipped_free_tier"
    needs_review = "needs_review"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(PipelineRunStatus), nullable=False, default=PipelineRunStatus.pending
    )
    current_stage: Mapped[str] = mapped_column(String(50), nullable=True)
    failed_at_stage: Mapped[str] = mapped_column(String(50), nullable=True)
    config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    total_documents: Mapped[int] = mapped_column(Integer, nullable=True)
    reprocess_all: Mapped[bool] = mapped_column(default=False)
    incremental: Mapped[bool] = mapped_column(Boolean, default=False)
    incremental_doc_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    tier_at_run: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    paused_at_stage: Mapped[str] = mapped_column(String(50), nullable=True)
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=True)

    workspace = relationship("Workspace", back_populates="pipeline_runs")
    stage_logs = relationship(
        "PipelineStageLog",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
        order_by="PipelineStageLog.started_at",
    )
    report = relationship("Report", back_populates="pipeline_run", uselist=False)
    stage_reviews = relationship(
        "StageReview",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
        order_by="StageReview.created_at",
    )


class PipelineStageLog(Base):
    __tablename__ = "pipeline_stage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(PipelineStageStatus), nullable=False, default=PipelineStageStatus.pending
    )
    output_summary: Mapped[dict] = mapped_column(JSON, nullable=True)
    errors: Mapped[str] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    pipeline_run = relationship("PipelineRun", back_populates="stage_logs")
