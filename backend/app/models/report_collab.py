"""Report collaboration models — DEPRECATED (Direção E · Onda 1 · M2).

Histórico (ADR-123 · Fase 6.5): entidades editáveis pelo usuário
dentro do relatório premium — `ReportNotes` (T6, 1:1 com report) e
`KanbanItem` (T3, N:1 com report). Persistidos no backend em vez de
localStorage para habilitar multi-dispositivo. Stateless rigoroso
(ADR-111) — estado vive no DB.

**Sunset (ADR-154 · M2 — 2026-04-29):** Modo Tático foi removido
(ADR-151), aggregates foram migrados para `Task` + `WorkspaceNotes`
(M1). Tabelas físicas renomeadas para `_legacy_kanban_items` /
`_legacy_report_notes` (RENAME, dado preservado). Estes models
permanecem apontando para as tabelas legadas **apenas** porque
`backend/app/services/internal_ops/purge_reports.py` ainda faz
DELETE em ambas no fluxo de purga de relatórios — limpa qualquer
remanescente. Após drop final em PR M3 (sprint+2, ~2026-05-13),
models e DELETE serão removidos.

Endpoints REST (`reports_collab.py`) já retornam HTTP 410 Gone.
Frontend não consome mais desde a Onda 3 (commit `cf14af6`).
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

    __tablename__ = "_legacy_report_notes"  # ADR-154 M2 sunset (2026-04-29)

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

    __tablename__ = "_legacy_kanban_items"  # ADR-154 M2 sunset (2026-04-29)

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
