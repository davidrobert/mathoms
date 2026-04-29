"""Task model — ADR-074.

Entidade de 1ª classe para o backlog de ações do workspace. Antes de F8,
essas tarefas viviam em `config/tarefas.md` e eram parseadas pelo E5
(deterministicamente) para renderizar o checklist no relatório. Esse
fluxo era incompatível com execução interativa (marcar "feito", anexar
comprovante, ser notificado de prazo).

A partir de F8.2:
- `tarefas.md` vira export gerado sob demanda (compat pipeline legado)
- E5.N passa a escrever em `task_suggestions` (aprovação 1-click)
- Relatório lê **snapshot imutável** copiado no momento da geração

Campos-chave:
- `number`: preserva o # histórico do tarefas.md (1..43), único por workspace
- `priority`: S/R/O (Essencial/Recomendada/Opcional) — mesmo vocabulário do MD
- `deadline_kind`: HARD_DATE | MONTH | QUARTER | CONDITIONAL | UNSCHEDULED
  + `deadline_date` (só para HARD_DATE) + `deadline_label` (texto livre
  para "Antes EUA", "T3/26", etc.)
- `parent_task_id`: dependência explícita — UI bloqueia done se parent pendente
- `related_transaction_id` / `related_goal_id`: links para dados financeiros
  (F8.3+: dashboards podem mostrar "% executado")
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
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

# Vocabulários — mantidos como frozenset para evitar migrations ao
# adicionar categorias. Validação no service layer.
VALID_PRIORITIES: frozenset[str] = frozenset({"S", "R", "O"})

VALID_CATEGORIES: frozenset[str] = frozenset(
    {
        "Invest",
        "Orcamento",
        "Tributario",
        "Seguros",
        "Imoveis",
        "Financeiro",
        "Plan. EUA",
        "Juridico",
        "Sucessorio",
        "Pipeline",
    }
)

# Transições válidas. `done` e `cancelled` são terminais — para reabrir,
# caller precisa mudar status explicitamente via service (audit trail).
VALID_STATUSES: frozenset[str] = frozenset(
    {"pending", "in_progress", "done", "cancelled", "blocked"}
)

VALID_DEADLINE_KINDS: frozenset[str] = frozenset(
    {"HARD_DATE", "MONTH", "QUARTER", "CONDITIONAL", "UNSCHEDULED"}
)

VALID_CREATED_FROM: frozenset[str] = frozenset(
    {"manual", "seed", "llm_suggestion", "kanban_migration"}
)

# board_column é o eixo tático do Kanban (ADR-153). NULL = task não vive
# no board view. Preenchido via aceite explícito do usuário ou backfill.
VALID_BOARD_COLUMNS: frozenset[str] = frozenset({"a_fazer", "em_andamento", "concluido"})

# urgency é o eixo tático ortogonal a `priority` (S/R/O metodológico).
# Migrado de KanbanItem.prioridade. Opt-in para tasks novas (NULL ok).
VALID_URGENCIES: frozenset[str] = frozenset({"alta", "media", "baixa"})

VALID_SUGGESTION_STATUSES: frozenset[str] = frozenset({"pending", "approved", "rejected", "merged"})

VALID_SUGGESTION_SOURCES: frozenset[str] = frozenset({"e5n_llm", "cross_validation", "system_rule"})


class Task(Base):
    """Tarefa ativa no backlog do workspace."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # # histórico do tarefas.md (1..43). Único por workspace (ver index abaixo).
    # Novas tasks criadas pela UI recebem max(number)+1.
    number: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(1), nullable=False, index=True)

    deadline_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="UNSCHEDULED")
    deadline_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    deadline_label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    status_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    parent_task_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Links opcionais (F8.3+) — não criam FK real a transactions/goals por
    # ora porque essas tabelas também estão evoluindo; guardamos IDs
    # livres para serem tipados/validados via service.
    related_transaction_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    related_goal_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
    )

    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_from: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_suggestion_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # ADR-153: Kanban view; NULL = task fora do board. Backfill preserva coluna.
    board_column: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    board_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ADR-153: eixo tático ortogonal a priority (S/R/O); opt-in.
    urgency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    # ADR-153: ON DELETE SET NULL preserva task ao deletar o relatório de origem.
    origin_report_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ADR-153: filtra tasks de Kanban migrado em widgets (UpcomingTasksWidget).
    is_board_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(
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
    parent = relationship("Task", remote_side="Task.id", backref="children")
    creator = relationship("User")
    related_goal = relationship("Goal")
    attachments = relationship(
        "TaskAttachment", back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "number", name="uq_task_ws_number"),
        Index("ix_tasks_ws_status_deadline", "workspace_id", "status", "deadline_date"),
        Index("ix_tasks_ws_priority_status", "workspace_id", "priority", "status"),
        Index("ix_tasks_ws_board_column", "workspace_id", "board_column"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Task #{self.number} ws={self.workspace_id} status={self.status}>"


class TaskSuggestion(Base):
    """Sugestão de tarefa gerada pelo E5.N ou regras do sistema, aguardando
    aprovação humana. Quando aprovada, materializa uma `Task`."""

    __tablename__ = "task_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Payload proposto — mesma shape que `TaskCreate` (validado no approve)
    proposed_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Populado ao aprovar (FK para a Task criada)
    approved_task_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workspace = relationship("Workspace")
    approved_task = relationship("Task", foreign_keys=[approved_task_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (Index("ix_suggestions_ws_status", "workspace_id", "status"),)


class TaskAttachment(Base):
    """Anexo de uma tarefa (comprovante, contrato, nota fiscal).

    Referencia objeto no vault storage para manter criptografia at-rest
    consistente com resto do produto.
    """

    __tablename__ = "task_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Caminho relativo no storage/{workspace_id}/... — consistente com
    # documentos e vault.
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    uploaded_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    task = relationship("Task", back_populates="attachments")
    uploader = relationship("User")
