"""Risk model — ADR-178 (workspace-scoped aggregate).

Aggregate paralelo a ``Decision`` (ADR-136). Decision = ação a tomar;
Risk = evento incerto que pode (ou não) ocorrer. Distinção semântica
forte: link causa↔mitigação via ``mitigations_decision_ids`` (array de
Decision.id em JSON).

Status:
    Ativo       — risco identificado, ainda não mitigado/aceito.
    Mitigado    — coberto por uma ou mais Decisions (consultor confirma).
    Aceito      — cliente decidiu conviver com o risco (custo de mitigar
                  é maior que impacto esperado).
    Descartado  — não se aplica ao cliente (avaliado e descartado).

``probability`` (qualitativo) — cliente preenche; null quando aceito mas
ainda não calibrado. ``impact_level`` (qualitativo) — sempre presente.
``impact_brl_cents`` (quantitativo opcional) — Money em BIGINT cents
(ADR-090) quando o cliente quantifica.

Multi-tenancy: ``UNIQUE (workspace_id, code)`` — ``code`` é slug estável
por workspace ("morte", "invalidez_provedor"); o mesmo código pode existir
em workspaces diferentes.

NÃO é event-sourced por escolha (v1 — ADR-178 §"Trade-offs"). ``updated_at``
basta; demanda futura de event log gera ADR de extensão.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
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

VALID_RISK_PROBABILITIES: frozenset[str] = frozenset({"baixa", "média", "alta"})

VALID_RISK_IMPACT_LEVELS: frozenset[str] = frozenset({"baixo", "médio", "alto", "crítico"})

VALID_RISK_STATUSES: frozenset[str] = frozenset({"Ativo", "Mitigado", "Aceito", "Descartado"})


class Risk(Base):
    """Risco workspace-scoped (ADR-178).

    Decision = ação a tomar. Risk = evento incerto. Link via
    ``mitigations_decision_ids`` (array de Decision.id).
    """

    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    probability: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    impact_level: Mapped[str] = mapped_column(String(16), nullable=False)
    impact_brl_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Ativo")
    # Array of Decision.id (UUID strings). JSON livre — modelagem
    # explicita N:M sem tabela auxiliar (ADR-178 §"Trade-offs": v1 sem
    # event-sourcing; lista direta é suficiente).
    mitigations_decision_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
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

    __table_args__ = (
        UniqueConstraint("workspace_id", "code", name="uq_risks_workspace_code"),
        Index("ix_risks_ws_status", "workspace_id", "status"),
        Index("ix_risks_ws_impact", "workspace_id", "impact_level"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Risk ws={self.workspace_id} code={self.code} status={self.status}>"
