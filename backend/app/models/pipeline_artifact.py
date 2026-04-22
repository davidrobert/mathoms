"""PipelineArtifact — artefatos computacionais produzidos por cada stage do pipeline.

ADR-082. Substitui artefatos em ``processed/*.json`` por registros no banco com FK a
``pipeline_runs`` e, quando aplicável, a ``documents``. Permite:

- Eliminar acoplamento por nome de arquivo (``_find_e2_extract`` & cia.)
- Modo incremental determinístico via ``pipeline_last_run_at IS NULL``
- Histórico auditável de artefatos por run

Durante Fases 1-8, a coluna ``stage`` usa nomes legados (``"E2"``, ``"E3"``...).
A Fase 9 renomeia para identificadores descritivos (``"extract_statements"``,
``"reconcile_transactions"``...). Ver ``pipeline/stage_spec.py``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class PipelineArtifact(Base):
    """Artefato computacional produzido por um stage do pipeline.

    Campos-chave:
        stage:        identificador do stage (``"E2"``, ``"E3"``... nas Fases 1-8;
                      ``"extract_statements"``, ``"reconcile_transactions"`` pós-Fase 9).
        artifact_key: stem do documento (E2) ou nome canônico (E3+).
        document_id:  FK opcional — apenas para stages de extração (E2-*).
        content_json: payload do artefato (JSONB em Postgres, JSON em SQLite).
    """

    __tablename__ = "pipeline_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    artifact_key: Mapped[str] = mapped_column(String(255), nullable=False)

    document_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    byte_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    pipeline_run = relationship("PipelineRun")
    document = relationship("Document", foreign_keys=[document_id])

    __table_args__ = (
        UniqueConstraint(
            "pipeline_run_id",
            "stage",
            "artifact_key",
            name="uq_pipeline_artifacts_run_stage_key",
        ),
        Index(
            "ix_pipeline_artifacts_workspace_stage_key",
            "workspace_id",
            "stage",
            "artifact_key",
        ),
        Index(
            "ix_pipeline_artifacts_document_id",
            "document_id",
        ),
    )
