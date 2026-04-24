"""Report collaboration models — ADR-123 · Fase 6.5.

Entidades editáveis pelo usuário dentro do relatório premium:

- ``ReportNotes`` (T6) — textarea de anotações por relatório.
  1:1 com report (unique em ``(workspace_id, report_id)``).
- ``KanbanItem`` (T3) — tarefas arrastáveis no Kanban tático.
  N:1 com report.

Decisão (ADR-123): persistir no backend em vez de localStorage para
habilitar multi-dispositivo e exportação. Continua stateless rigoroso
(ADR-111) — estado vive no DB, não em módulo global.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

VALID_PRIORIDADE: frozenset[str] = frozenset({"alta", "media", "baixa"})
VALID_COLUNA: frozenset[str] = frozenset({"a_fazer", "em_andamento", "concluido"})
VALID_ESSENCIAL: frozenset[str] = frozenset({"S", "R", "O"})


class ReportNotes(Base):
    """Anotações livres por relatório (T6 do shell premium)."""

    __tablename__ = "report_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
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
    author = relationship("User")

    __table_args__ = (
        UniqueConstraint("workspace_id", "report_id", name="uq_report_notes_ws_report"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ReportNotes report={self.report_id} len={len(self.content)}>"


class KanbanItem(Base):
    """Item do Kanban tático do relatório premium (T3)."""

    __tablename__ = "kanban_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    coluna: Mapped[str] = mapped_column(String(32), nullable=False, default="a_fazer")
    prioridade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    prazo: Mapped[date | None] = mapped_column(Date, nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(64), nullable=True)
    essencial: Mapped[str | None] = mapped_column(String(1), nullable=True)
    # Ordem relativa dentro da coluna (para DnD future).
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    creator = relationship("User")

    __table_args__ = (
        Index("ix_kanban_items_ws_report_col", "workspace_id", "report_id", "coluna"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<KanbanItem report={self.report_id} col={self.coluna} titulo={self.titulo!r}>"
