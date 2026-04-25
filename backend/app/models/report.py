"""Report model — represents a generated financial report."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
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
    # ADR-131: FK ao artefato E5 em ``pipeline_artifacts``. Substitui o
    # campo legado ``analysis_json_path`` (filesystem). ``SET NULL`` no
    # delete do artifact preserva a linha do Report mesmo se o run for
    # hard-deleted; o endpoint ``/reports/{id}/data`` retorna 404 nesse caso.
    analysis_artifact_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("pipeline_artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    # F8.3 / ADR-074: snapshot imutável da lista de tasks no momento em que
    # o relatório foi gerado. Permite ao relatório renderizar "tarefas relatadas
    # em 15/abr/2026" mesmo que o backlog tenha mudado depois. Nullable = pré-F8.3.
    tasks_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # F11.6b — referência às premissas vigentes (metas + hash do goals.json) para comparar relatórios.
    premissas_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    patrimonio_liquido: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspace = relationship("Workspace", back_populates="reports")
    pipeline_run = relationship("PipelineRun", back_populates="report")
    analysis_artifact = relationship(
        "PipelineArtifact",
        foreign_keys=[analysis_artifact_id],
        lazy="joined",
    )
