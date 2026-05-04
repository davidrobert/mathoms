"""Command DTOs do agregado ``Decision`` (ADR-136).

Money no wire em string decimal (ADR-090). Conversão para
``amount_brl_cents`` (BIGINT) acontece no use case via ``Money``-like
helper (cents = round(Decimal(str(brl)) * 100)).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.decision import VALID_DECISION_STATUSES, VALID_TARGET_VALUE_TYPES


class DecisionCreateCommand(BaseModel):
    """Cria nova ``Decision`` (status inicial = ``Pendente`` se omitido)."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=16)
    title: str = Field(..., min_length=1, max_length=500)
    rationale: Optional[str] = None
    amount_brl: Optional[Decimal] = Field(
        None, description="Valor em BRL (string decimal). Convertido para cents."
    )
    status: str = "Pendente"
    decided_at: Optional[date] = None
    # ADR-162 — projection target.
    target_field: Optional[str] = Field(None, max_length=64)
    target_value: Optional[str] = Field(None, max_length=128)
    target_value_type: Optional[str] = Field(None, max_length=8)
    # ADR-163 — KPIs frozen do relatório-fonte.
    context_snapshot: Optional[dict] = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        if v not in VALID_DECISION_STATUSES:
            raise ValueError(f"status inválido: {v!r}; aceitos: {sorted(VALID_DECISION_STATUSES)}")
        return v

    @field_validator("target_value_type")
    @classmethod
    def _validate_target_value_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_TARGET_VALUE_TYPES:
            raise ValueError(
                f"target_value_type inválido: {v!r}; aceitos: {sorted(VALID_TARGET_VALUE_TYPES)}"
            )
        return v


class DecisionUpdateCommand(BaseModel):
    """Atualiza campos editoriais. Status muda via /execute ou /supersede."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    rationale: Optional[str] = None
    amount_brl: Optional[Decimal] = None
    status: Optional[str] = None
    decided_at: Optional[date] = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_DECISION_STATUSES:
            raise ValueError(f"status inválido: {v!r}; aceitos: {sorted(VALID_DECISION_STATUSES)}")
        return v


class DecisionExecuteCommand(BaseModel):
    """Marca a Decision como ``Executado``. ``executed_at`` default = hoje."""

    model_config = ConfigDict(extra="forbid")

    executed_at: Optional[date] = None
    note: Optional[str] = None


class DecisionSupersedeCommand(BaseModel):
    """Aponta uma Decision como substituída por outra (ID alvo).

    O caller informa o **id** da Decision que substitui ("nova"); o
    endpoint correspondente é ``POST /decisions/{old_id}/supersede``.
    """

    model_config = ConfigDict(extra="forbid")

    superseded_by_id: str = Field(..., min_length=36, max_length=36)
    note: Optional[str] = None
