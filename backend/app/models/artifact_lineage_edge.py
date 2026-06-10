"""ArtifactLineageEdge — índice reverso field-level derivado do ``_lineage`` E5 (ADR-279 · A25.l3): tabela **derivada/rebuildável** (retenção N=1 por workspace, B6), materializada por hook pós-run best-effort, nunca fonte primária — auditoria histórica usa o ``_lineage`` inline em ``pipeline_artifacts``. Sem ``created_at`` por design (determinístico, zero timestamp); ``data_source_id`` é coluna plain (FK Postgres-only na migration ``adr279edges``, padrão de ``pipeline_artifacts.data_source_id`` ADR-278)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class ArtifactLineageEdge(Base):
    """Edge ``src → dst`` do grafo de lineage do último run bem-sucedido do workspace: ``src_field == ""`` marca edge coarse de FOLHA documental (``edge_type == "source_document"`` — teto run→doc, não atribuição fina doc→campo); ``winner`` é ``True`` em toda edge derivada (semântica fina de sobrevivente de dedup K4 member-level é reservada a F7)."""

    __tablename__ = "artifact_lineage_edge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )

    src_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    src_key: Mapped[str] = mapped_column(String(255), nullable=False)
    src_field: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    dst_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    dst_key: Mapped[str] = mapped_column(String(255), nullable=False)
    dst_field: Mapped[str] = mapped_column(String(255), nullable=False)

    edge_type: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_ref: Mapped[str] = mapped_column(Text, nullable=False, default="")

    source_document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    data_source_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    winner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        # Load-bearing p/ o DELETE de retenção N=1 (writer) e p/ rebuild por run.
        Index("ix_artifact_lineage_edge_ws_run", "workspace_id", "run_id"),
        # Query reversa F5: "números que dependem da fonte X".
        Index("ix_artifact_lineage_edge_ws_doc", "workspace_id", "source_document_id"),
        # Índice (workspace_id, rule_ref) deferido junto com o MCP (coluna sim, índice não).
    )
