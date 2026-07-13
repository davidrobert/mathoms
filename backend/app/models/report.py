"""Report model — represents a generated financial report."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, text
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
    # ``score`` é índice 0–10 (não monetário) → Float é legítimo. Populado a
    # partir do artefato E5 (``score.valor``) na criação do Report (ADR-326).
    score: Mapped[float] = mapped_column(Float, nullable=True)
    # ADR-283 — agregado monetário (BRL consolidado). ``Numeric(18,2)`` honra
    # ADR-090 (dinheiro nunca é float); o read-path em goal_service já devolve
    # ``Decimal`` para o cálculo de meta IF.
    patrimonio_liquido: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # REL-03 — idempotência de Report sob redelivery do Celery (acks_late +
    # reject_on_worker_lost): worker-lost reenfileira a mensagem e o run
    # re-roda, recriando o Report. Índice único parcial é o backstop à prova
    # de corrida (a guarda de estado terminal em ``_mark_run_started`` é só
    # otimização). Parcial em ``IS NOT NULL`` porque ``pipeline_run_id`` é
    # nullable (run hard-deleted → SET NULL; múltiplos Reports órfãos são OK).
    __table_args__ = (
        Index(
            "ux_reports_workspace_pipeline_run",
            "workspace_id",
            "pipeline_run_id",
            unique=True,
            sqlite_where=text("pipeline_run_id IS NOT NULL"),
            postgresql_where=text("pipeline_run_id IS NOT NULL"),
        ),
    )

    workspace = relationship("Workspace", back_populates="reports")
    pipeline_run = relationship("PipelineRun", back_populates="report")
    analysis_artifact = relationship(
        "PipelineArtifact",
        foreign_keys=[analysis_artifact_id],
        lazy="joined",
    )

    @staticmethod
    def denorm_from_analysis(content: object) -> tuple[float | None, Decimal | None]:
        """Deriva ``score`` (0–10) e ``patrimonio_liquido`` (Decimal) do artefato E5 decriptado; ausente/malformado ⇒ ``None`` (ADR-326)."""
        if not isinstance(content, dict):
            return None, None
        score = None
        score_block = content.get("score")
        if isinstance(score_block, dict) and isinstance(score_block.get("valor"), (int, float)):
            score = float(score_block["valor"])
        patrimonio_liquido = None
        pat_block = content.get("patrimonio")
        if isinstance(pat_block, dict) and pat_block.get("liquido") is not None:
            patrimonio_liquido = Decimal(str(pat_block["liquido"]))
        return score, patrimonio_liquido
