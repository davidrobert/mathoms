"""PlannerReview — metadata projection sobre ``pipeline_artifacts`` (ADR-199 §D3 + ADR-204). Invariantes lógicos validados no service layer; ver ``backend/app/application/planner_review/`` (Ato 4)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

VALID_PLANNER_REVIEW_STATUSES: frozenset[str] = frozenset(
    {"Pendente", "Gerado", "Publicado", "Superseded"}
)

VALID_TIERS: frozenset[str] = frozenset({"free", "premium"})


# Eixo ORTOGONAL a ``status``: este é o desfecho da geração, aquele é publicação
# (ADR-204 §D1). Não se fundem porque ``entregue_com_retencao`` é publicável —
# como valor de ``status`` daria 409 no publish de um parecer publicável.
class ParecerOutcome(str, enum.Enum):
    """Desfecho da geração do parecer (ADR-366 §D1)."""

    entregue = "entregue"
    entregue_com_retencao = "entregue_com_retencao"
    retido = "retido"
    # Default de coluna: writer que não declara o desfecho não afirma completude.
    nao_registrado = "nao_registrado"


# Nasce argumento obrigatório do construtor do desfecho — nunca derivado de parse
# de ``error_detail``, cuja prosa carrega o próprio termo §13 no ramo de sigilo.
class ParecerRetentionReason(str, enum.Enum):
    """Motivo client-facing da retenção, namespaced como ADR-272 (ADR-366 §D3)."""

    citacao_nao_confirmada = "parecer.citacao_nao_confirmada"
    sigilo = "parecer.sigilo"
    conselho_vedado = "parecer.conselho_vedado"


# ``retention_reason`` é NULL exatamente nesses desfechos (ADR-366 §D3).
OUTCOMES_WITHOUT_REASON: frozenset[ParecerOutcome] = frozenset(
    {ParecerOutcome.entregue, ParecerOutcome.nao_registrado}
)


class PlannerReview(Base):
    """Metadata projection do parecer planejador (ADR-199 §D3)."""

    __tablename__ = "planner_review_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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
    # Artifact com o conteúdo do parecer (E6-parecer/parecer_planejador) — fonte de verdade.
    pipeline_artifact_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pipeline_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Lineage: artifact E5 que alimentou a geração (ADR-199 §D2).
    e5_artifact_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pipeline_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Lifecycle (ADR-204 §D1). Texto livre validado no service via frozenset.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pendente", index=True)

    # Supersedure chain (ADR-204 §D3). FK self-ref + back-pointer denormalizado
    # (``superseded_by_id``) para evitar JOIN reverso em SELECT temporal.
    supersedes_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("planner_review_metadata.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    superseded_by_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Persona + manifest auditoria (ADR-200/201).
    persona_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_version: Mapped[str] = mapped_column(String(20), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Imutabilidade pós-publicação (ADR-204 §D2). SHA-256 do content_json no momento
    # da transição Gerado → Publicado.
    immutable_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Gating freemium (ADR-208 §D2/§D3).
    tier_at_generation: Mapped[str] = mapped_column(String(20), nullable=False)
    items_shown_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_gated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Desfecho da geração (ADR-366 §D1). Default fail-honest: o writer que não
    # declara não passa a afirmar completude.
    outcome: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ParecerOutcome.nao_registrado.value,
        server_default=ParecerOutcome.nao_registrado.value,
    )
    retention_reason: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)
    # Retenção por qualidade (ADR-295 per-item) — generation-scoped, ao contrário
    # de ``items_shown_count``, que a API recomputa pós-tier (ADR-366 §D4).
    items_dropped_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # FinOps (ADR-208 + plano §Métricas). Money em cents (ADR-090).
    cost_usd_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Audit.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    workspace = relationship("Workspace")
    pipeline_run = relationship("PipelineRun")
    pipeline_artifact = relationship("PipelineArtifact", foreign_keys=[pipeline_artifact_id])
    e5_artifact = relationship("PipelineArtifact", foreign_keys=[e5_artifact_id])
    supersedes = relationship(
        "PlannerReview",
        remote_side="PlannerReview.id",
        foreign_keys=[supersedes_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "pipeline_run_id",
            name="uq_planner_review_workspace_run",
        ),
        Index(
            "ix_planner_review_workspace_status",
            "workspace_id",
            "status",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PlannerReview ws={self.workspace_id} run={self.pipeline_run_id} "
            f"status={self.status} outcome={self.outcome} tier={self.tier_at_generation}>"
        )
