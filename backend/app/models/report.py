"""Report model — represents a generated financial report."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    period: Mapped[str] = mapped_column(String(50), nullable=True)
    html_path: Mapped[str] = mapped_column(Text, nullable=False)
    # Path to the E5 analysis JSON snapshot (ADR-076 / F9): enables the native
    # React report view to consume structured data instead of parsing HTML.
    # Nullable for backward-compat with pre-F9 reports where only html_path existed.
    analysis_json_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # F8.3 / ADR-074: snapshot imutável da lista de tasks no momento em que
    # o relatório foi gerado. Permite ao relatório renderizar "tarefas relatadas
    # em 15/abr/2026" mesmo que o backlog tenha mudado depois. Nullable = pré-F8.3.
    tasks_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # F11.6b — referência às premissas vigentes (metas + hash do goals.json) para comparar relatórios.
    premissas_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    patrimonio_liquido: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspace = relationship("Workspace", back_populates="reports")
    pipeline_run = relationship("PipelineRun", back_populates="report")
