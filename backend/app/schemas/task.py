"""Pydantic schemas para Task, TaskSuggestion (ADR-074)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DeadlineKind = Literal[
    "HARD_DATE", "MONTH", "QUARTER", "CONDITIONAL", "UNSCHEDULED"
]

TaskStatus = Literal["pending", "in_progress", "done", "cancelled", "blocked"]

Priority = Literal["S", "R", "O"]

CreatedFrom = Literal["manual", "seed", "llm_suggestion"]

SuggestionStatus = Literal["pending", "approved", "rejected", "merged"]

SuggestionSource = Literal["e5n_llm", "cross_validation", "system_rule"]


# ─── Task ──────────────────────────────────────────────────────────────


class TaskBase(BaseModel):
    """Campos comuns entre create/update/response."""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=64)
    priority: Priority
    deadline_kind: DeadlineKind = "UNSCHEDULED"
    deadline_date: Optional[date] = None
    deadline_label: Optional[str] = Field(None, max_length=128)
    ref: Optional[str] = Field(None, max_length=255)
    parent_task_id: Optional[str] = None
    related_transaction_id: Optional[str] = None
    related_goal_id: Optional[str] = None
    assigned_to: Optional[str] = None


class TaskCreate(TaskBase):
    """Body do POST — number é auto-atribuído pelo service."""

    # Opcional: caller pode forçar um # específico (para importer).
    # Se ausente, service usa max(number)+1 por workspace.
    number: Optional[int] = None


class TaskUpdate(BaseModel):
    """PATCH parcial. Todos os campos opcionais."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=64)
    priority: Optional[Priority] = None
    deadline_kind: Optional[DeadlineKind] = None
    deadline_date: Optional[date] = None
    deadline_label: Optional[str] = Field(None, max_length=128)
    ref: Optional[str] = Field(None, max_length=255)
    parent_task_id: Optional[str] = None
    related_transaction_id: Optional[str] = None
    related_goal_id: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[TaskStatus] = None
    status_reason: Optional[str] = None


class TaskStatusTransition(BaseModel):
    """Body dedicado para transição de status — permite rastrear motivo."""

    status: TaskStatus
    status_reason: Optional[str] = Field(None, max_length=1000)


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    number: int
    status: TaskStatus
    status_reason: Optional[str] = None
    created_from: CreatedFrom
    source_suggestion_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int


# ─── TaskSuggestion ────────────────────────────────────────────────────


class TaskSuggestionProposed(TaskBase):
    """Shape do payload proposto pela LLM. Idêntico a TaskCreate exceto
    por não aceitar `number` (importer-only)."""

    pass


class TaskSuggestionCreate(BaseModel):
    """Body do POST interno (E5.N→DB)."""

    proposed_payload: TaskSuggestionProposed
    source: SuggestionSource
    source_run_id: Optional[str] = None


class TaskSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    proposed_payload: dict
    source: SuggestionSource
    source_run_id: Optional[str] = None
    status: SuggestionStatus
    rejection_reason: Optional[str] = None
    approved_task_id: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class TaskSuggestionListResponse(BaseModel):
    suggestions: list[TaskSuggestionResponse]
    total: int


class TaskSuggestionApprove(BaseModel):
    """Body do POST /approve — opcionalmente usuário edita antes de aceitar."""

    edited_payload: Optional[TaskSuggestionProposed] = None


class TaskSuggestionReject(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000)


# ─── Filtros / Listagem ────────────────────────────────────────────────


class TaskFilters(BaseModel):
    """Query params aceitos pelo GET /tasks. Todos opcionais."""

    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    category: Optional[str] = None
    deadline_before: Optional[date] = None
    deadline_after: Optional[date] = None
    assigned_to: Optional[str] = None
    related_goal_id: Optional[str] = None
    include_done: bool = False
    include_cancelled: bool = False


# ─── Task Progress (F8.3 — Task↔Transaction) ──────────────────────────


class TaskProgress(BaseModel):
    """Progresso de execução de uma tarefa, derivado de transações do mês.

    Só faz sentido para tasks acionáveis recorrentes (ex: "Configurar
    aporte R$20k/mês"). Para tasks binárias (sem métrica), todos os
    campos são None.
    """

    is_trackable: bool = Field(
        ...,
        description="True se temos heurística para medir % executado.",
    )
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    target_brl: Optional[float] = Field(
        None,
        description="Valor-alvo do período (ex: aporte mensal R$ 20.000).",
    )
    executed_brl: Optional[float] = Field(
        None,
        description="Valor efetivamente movimentado no período (abs).",
    )
    percent_executed: Optional[float] = Field(
        None, description="0..100+ (pode passar de 100 se superou)."
    )
    matched_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords que dispararam o match da task (debug/UI).",
    )
    matched_transactions_count: int = 0


# ─── Task Attachments (F8.3) ──────────────────────────────────────────


class TaskAttachmentResponse(BaseModel):
    """Metadados de um anexo. O binário é servido por `GET /download`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    workspace_id: str
    original_filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_by: Optional[str] = None
    created_at: datetime


class TaskAttachmentListResponse(BaseModel):
    attachments: list[TaskAttachmentResponse]
    total: int
