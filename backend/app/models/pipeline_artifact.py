"""PipelineArtifact — artefatos computacionais produzidos por cada stage do pipeline.

ADR-082. Substitui artefatos em ``processed/*.json`` por registros no banco com FK a
``pipeline_runs`` e, quando aplicável, a ``documents``. Permite:

- Eliminar acoplamento por nome de arquivo (``_find_e2_extract`` & cia.)
- Modo incremental determinístico via ``pipeline_last_run_at IS NULL``
- Histórico auditável de artefatos por run

Durante Fases 1-8, a coluna ``stage`` usa nomes legados (``E2``, ``E3``...).
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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class PipelineArtifact(Base):
    """Artefato computacional produzido por um stage do pipeline.

    Campos-chave:
        stage:        identificador do stage (``E2``, ``E3``... nas Fases 1-8;
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
    # ADR-278: fonte canônica plugável (coarse). ``document_id`` permanece como folha
    # fina; generaliza a origem (document hoje, feed Open Finance amanhã). O FK DB
    # (ON DELETE SET NULL) é Postgres-específico e entra na lane dl-f1-migration-runbook;
    # aqui a coluna é nullable indexada e a integridade é garantida no app layer.
    data_source_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # ADR-311: versão de extração consultável (PROMPT_VERSION do writer LLM),
    # lift do payload em DBArtifactStore.write — NUNCA entra na artifact_key
    # (quebraria o dedupe por documento, ADR-080). NULL ≡ versão desconhecida/0
    # (rows pré-migration, sem backfill de conteúdo).
    prompt_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    byte_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # A33.l6 (W6-T05) — retenção por idade de row superseded. NULL ≡ fail-safe:
    # nunca prunável. A versão corrente por (workspace, stage, artifact_key)
    # fica NULL permanentemente; o write de uma nova corrente marca a anterior
    # (DBArtifactStore._mark_superseded). Prune diário só deleta
    # retention_until < now, com defesa em profundidade (nunca a corrente,
    # nunca row referenciada por reports/planner_review/publications).
    retention_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
        # ADR-241 — `_get_latest_in_workspace` faz ORDER BY created_at DESC,
        # id DESC LIMIT 1; sem este índice é seq scan + sort em memória. Com a
        # promoção de E2 a workspace-scoped, esse caminho vira hot path.
        # O tie-break por id não exige coluna no índice: o prefixo de igualdade
        # + created_at continua servindo o scan; empates são raros e o sort
        # incremental do top-1 é desprezível.
        Index(
            "ix_pipeline_artifacts_ws_stage_key_created",
            "workspace_id",
            "stage",
            "artifact_key",
            "created_at",
        ),
        Index(
            "ix_pipeline_artifacts_document_id",
            "document_id",
        ),
        # ADR-278: lineage reverso (F7) consulta artefatos por fonte.
        Index(
            "ix_pipeline_artifacts_data_source_id",
            "data_source_id",
        ),
        # A33.l6 — índice parcial para o prune diário (WHERE retention_until
        # IS NOT NULL AND retention_until < now). A maioria das rows é NULL
        # (corrente/fail-safe); índice cheio seria desperdício.
        Index(
            "ix_pipeline_artifacts_retention_until",
            "retention_until",
            postgresql_where=text("retention_until IS NOT NULL"),
            sqlite_where=text("retention_until IS NOT NULL"),
        ),
    )
