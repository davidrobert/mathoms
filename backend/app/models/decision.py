"""Decision model — ADR-136 (event-sourced).

Aggregate editorial do plano de ação financeiro. Cada `Decision` é
projeção; o histórico vive em `decision_events` (append-only). Use
cases nunca atualizam status ``in-place`` sem emitir evento — isso é
invariante do aggregate.

Status:
    Pendente       — proposta, ainda não decidida.
    Decidido       — decisão confirmada; aguarda execução.
    Executado      — ação realizada (com `executed_at`).
    Descartado     — abandonada (não será executada).
    Superseded     — substituída por outra Decision via
                     `SupersedeDecision`. `supersedes_id` da nova aponta
                     para a antiga.

Money em ``amount_brl_cents`` (BIGINT) — ADR-090. ``None`` quando a
decisão não tem valor monetário (ex.: terminologia, manter serviço).

Multi-tenancy: ``UNIQUE (workspace_id, code)`` — `code` ("D01", "D15") é
estável por workspace, mas o mesmo código pode existir em workspaces
diferentes.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

VALID_DECISION_STATUSES: frozenset[str] = frozenset(
    {"Pendente", "Decidido", "Executado", "Descartado", "Superseded"}
)

VALID_DECISION_EVENT_TYPES: frozenset[str] = frozenset(
    {"Created", "StatusChanged", "Superseded", "Executed", "Updated", "GoalProjected"}
)

# ADR-162 — tipos de valor aceitos no `target_value` para parsing.
VALID_TARGET_VALUE_TYPES: frozenset[str] = frozenset({"pct", "brl", "int", "str"})


class Decision(Base):
    """Decisão editorial do workspace (event-sourced — ADR-136)."""

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amount_brl_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    supersedes_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("decisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    executed_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # ADR-162 — projection target. Quando populado, marcar Decision como
    # ``Executado`` cria nova versão do Goal correspondente na mesma
    # transação. Ver `backend.app.services.decision_goal_projection`.
    target_field: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_value: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    target_value_type: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    # ADR-163 — KPIs frozen do relatório que originou a Suggestion (quando
    # Decision veio de aceitar Suggestion). JSON livre para evoluir.
    context_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
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
    superseded_by_chain = relationship(
        "Decision",
        remote_side="Decision.id",
        foreign_keys=[supersedes_id],
    )
    events = relationship(
        "DecisionEvent",
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="DecisionEvent.occurred_at",
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "code", name="uq_decisions_workspace_code"),
        Index("ix_decisions_ws_status", "workspace_id", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Decision ws={self.workspace_id} code={self.code} status={self.status}>"


class DecisionEvent(Base):
    """Append-only event log do aggregate Decision."""

    __tablename__ = "decision_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    decision = relationship("Decision", back_populates="events")

    __table_args__ = (Index("ix_decision_events_decision_occurred", "decision_id", "occurred_at"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DecisionEvent decision={self.decision_id} type={self.event_type}>"
