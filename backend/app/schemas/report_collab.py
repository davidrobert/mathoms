"""Schemas — report collaboration (ADR-123 · Fase 6.5).

Pydantic DTOs para os endpoints de Notas (T6) e Kanban (T3) do relatório
premium. Separados em tipos Read/Write por boundary (ADR-102 R18).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


KanbanColuna = Literal["a_fazer", "em_andamento", "concluido"]
KanbanPrioridade = Literal["alta", "media", "baixa"]
KanbanEssencial = Literal["S", "R", "O"]


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


# ─── Notes ───────────────────────────────────────────────────────────


class ReportNotesRead(_Base):
    id: str
    report_id: str
    content: str
    author_user_id: str | None = None
    updated_at: datetime


class ReportNotesWrite(BaseModel):
    """PUT body — idempotente (upsert). Sem id no path (1:1 com report)."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., max_length=20000)


# ─── Kanban ──────────────────────────────────────────────────────────


class KanbanItemRead(_Base):
    id: str
    report_id: str
    titulo: str
    coluna: KanbanColuna
    prioridade: KanbanPrioridade | None = None
    prazo: date | None = None
    categoria: str | None = None
    essencial: KanbanEssencial | None = None
    ordem: int
    updated_at: datetime


class KanbanItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(..., min_length=1, max_length=500)
    coluna: KanbanColuna = "a_fazer"
    prioridade: KanbanPrioridade | None = None
    prazo: date | None = None
    categoria: str | None = Field(None, max_length=64)
    essencial: KanbanEssencial | None = None
    ordem: int = 0


class KanbanItemUpdate(BaseModel):
    """PATCH body — todos campos opcionais."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(None, min_length=1, max_length=500)
    coluna: KanbanColuna | None = None
    prioridade: KanbanPrioridade | None = None
    prazo: date | None = None
    categoria: str | None = Field(None, max_length=64)
    essencial: KanbanEssencial | None = None
    ordem: int | None = None


class KanbanItemListResponse(_Base):
    """Envelope — evita Liskov issues com response_model Array."""

    items: list[KanbanItemRead]
