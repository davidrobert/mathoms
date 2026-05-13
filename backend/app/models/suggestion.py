"""Suggestion model — ADR-153 (Direção E · Onda 5).

Aggregate ``Suggestion`` é uma proposta determinística produzida pelo
gerador E5. Conteúdo é **imutável** após inserção; apenas ``status``
e campos de transição (``accepted_decision_id``, ``dismissed_reason``,
``accepted_at``, ``dismissed_at``) mutam.

Ciclo de vida (state machine simples — não event-sourced):

    Pendente ─accept──────► Aceita     ┐
    Pendente ─modify──────► Modificada │ → terminal (Decision criada)
    Pendente ─dismiss─────► Descartada ┘ (terminal, com `dismissed_reason`)

Re-geração via :func:`pipeline.domain.services.suggestion_generator`
usa ``dedup_key`` para idempotência: hash determinístico que tolera
flutuação pequena de valor monetário (bucket de R$1k) ou percentual
(bucket de 5pp). Constraint `(workspace_id, dedup_key)` único quando
``status`` ∈ {Pendente, Aceita, Modificada}; Descartadas não bloqueiam
re-aparecer após `DISMISS_RESPECT_WINDOW_DAYS` (90).

Money em ``amount_brl_cents`` (BIGINT) — ADR-090. ``None`` quando a
sugestão não tem valor monetário envolvido.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

VALID_SUGGESTION_AGGREGATE_STATUSES: frozenset[str] = frozenset(
    {"Pendente", "Aceita", "Modificada", "Descartada"}
)

VALID_SUGGESTION_SEVERITIES: frozenset[str] = frozenset({"info", "warning", "danger"})

VALID_SUGGESTION_ORIGINS: frozenset[str] = frozenset({"deterministic", "llm"})

VALID_DISMISS_REASONS: frozenset[str] = frozenset(
    {
        "ja_considerei",
        "nao_se_aplica",
        "discordo_diagnostico",
        "adiar",
        "outro",
    }
)

VALID_SUGGESTION_KINDS: frozenset[str] = frozenset(
    {
        # v1 (ADR-153)
        "trs_desalinhada",
        "reserva_insuficiente",
        "alocacao_fora_alvo",
        "aporte_abaixo_meta",
        # FP-003: dolarizacao_atrasada removida (ADR-168 — Modo USA removido).
        # v2 (ADR-161 — Onda 8)
        "endividamento_perigoso",
        "taxa_poupanca_caindo",
        "seguros_insuficientes",
        "concentracao_instituicao",
        "lifestyle_creep",
        "renda_passiva_real_baixa",
        # v3 — ADR-199 (parecer planejador, origin=llm). Kind único agrupa todas
        # as sugestões LLM; nuance vai em `category` (tema canônico) +
        # `rationale` (acao + impacto_qualitativo). Discriminator de fonte é
        # `origin='llm'`.
        "parecer_planejador",
    }
)

VALID_SUGGESTION_CATEGORIES: frozenset[str] = frozenset(
    {"alvo_if", "carteira", "protecao", "comportamental", "endividamento"}
)


class Suggestion(Base):
    """Sugestão imutável gerada por análise determinística do relatório."""

    __tablename__ = "suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    section_id: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    # ADR-161: agrupamento semântico cross-kind (ex.: trs_desalinhada e
    # aporte_abaixo_meta são ambos `alvo_if`). Nullable para compat com
    # registros pré-migration.
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="deterministic")
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    amount_brl_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Pendente")
    accepted_decision_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("decisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    dismissed_reason: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workspace = relationship("Workspace")
    report = relationship("Report", foreign_keys=[report_id])
    accepted_decision = relationship("Decision", foreign_keys=[accepted_decision_id])

    __table_args__ = (
        # Apenas pendente/aceita/modificada são únicas por dedup_key —
        # Descartadas não bloqueiam re-aparecer após janela.
        # SQLite não suporta WHERE em UNIQUE; SQLAlchemy emite o filter
        # como check em tempo de aplicação. Para Postgres, criamos índice
        # parcial via Alembic (ver migration adr153).
        Index("ix_sugagg_workspace_id", "workspace_id"),
        Index("ix_sugagg_ws_status", "workspace_id", "status"),
        Index("ix_sugagg_ws_dedup", "workspace_id", "dedup_key"),
        Index("ix_sugagg_ws_section", "workspace_id", "section_id"),
        UniqueConstraint(
            "workspace_id",
            "dedup_key",
            "status",
            name="uq_sugagg_ws_dedup_status",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Suggestion ws={self.workspace_id} kind={self.kind} "
            f"section={self.section_id} status={self.status}>"
        )
