"""PipelineRun and PipelineStageLog models — execution tracking."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

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

    # ADR-291 — run com from_stage lê stages run-scoped upstream deste run
    # base. NULL = run full/incremental/resume (sem base). SET NULL preserva
    # o run quando GC deletar o base (lineage degrada graciosamente).
    base_run_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )

    tier_at_run: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    paused_at_stage: Mapped[str] = mapped_column(String(50), nullable=True)
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=True)

    # ADR-172 (W2-T04) — heartbeat para detector de runs travados.
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

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
    """Execução de um stage — tabela de execuções do run, não espelho 1:1."""

    # Não há unique em `(pipeline_run_id, stage)` e dois call-sites de produção já
    # ordenam por `started_at DESC`: resume e redelivery produzem row nova, então
    # um run pode ter N execuções do mesmo stage — e revisões diferentes.

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

    # ADR-362 — revisão do processo que executou ESTE stage. NULL ≡ executor não
    # declarou (run pré-F1, CLI, teste, dev sem MATHOMS_BUILD_SHA); nunca
    # backfilled, porque inferir de `created_at` vs `git log` fabricaria dado.
    # Escrita só no INSERT: os caminhos terminais reescrevem `output_summary` por
    # atribuição total, e um run misto precisa preservar N valores distintos.
    # `String(48)` e não 20: `varchar` no Postgres REJEITA o INSERT acima do
    # limite, e `${{ github.sha }}` + `-dirty` dá 46 — largura folgada é a 2ª
    # camada de defesa atrás da normalização no boundary.
    executor_revision: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)

    pipeline_run = relationship("PipelineRun", back_populates="stage_logs")
