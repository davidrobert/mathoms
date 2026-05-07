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

from backend.app.models.decision import (
    VALID_DECISION_HORIZONS,
    VALID_DECISION_STATUSES,
    VALID_TARGET_VALUE_TYPES,
)

# ADR-179 — bounds de ``priority`` (sem persistência específica; SMALLINT
# aceita -32k..+32k mas UI/UX só faz sentido em 1..99).
_PRIORITY_MIN: int = 1
_PRIORITY_MAX: int = 99


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
    # ADR-179 — quantificação + horizonte + prioridade.
    impact_1y_brl: Optional[Decimal] = Field(
        None, description="Impacto financeiro em 1 ano (BRL string)."
    )
    impact_10y_brl: Optional[Decimal] = Field(
        None, description="Impacto financeiro em 10 anos (BRL string)."
    )
    horizon: Optional[str] = Field(
        None,
        max_length=16,
        description="Horizonte temporal: short_6_12m | medium_1_3y | long_5y_plus.",
    )
    priority: Optional[int] = Field(
        None, ge=_PRIORITY_MIN, le=_PRIORITY_MAX, description="1..99 (1 = mais urgente)."
    )

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

    @field_validator("horizon")
    @classmethod
    # WHY Optional sem default: Pydantic field_validator (assinatura imposta).
    def _validate_horizon(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_DECISION_HORIZONS:
            raise ValueError(f"horizon inválido: {v!r}; aceitos: {sorted(VALID_DECISION_HORIZONS)}")
        return v


class DecisionUpdateCommand(BaseModel):
    """Atualiza campos editoriais. Status muda via /execute ou /supersede."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    rationale: Optional[str] = None
    amount_brl: Optional[Decimal] = None
    status: Optional[str] = None
    decided_at: Optional[date] = None
    # ADR-179
    impact_1y_brl: Optional[Decimal] = None
    impact_10y_brl: Optional[Decimal] = None
    horizon: Optional[str] = Field(None, max_length=16)
    priority: Optional[int] = Field(None, ge=_PRIORITY_MIN, le=_PRIORITY_MAX)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_DECISION_STATUSES:
            raise ValueError(f"status inválido: {v!r}; aceitos: {sorted(VALID_DECISION_STATUSES)}")
        return v

    @field_validator("horizon")
    @classmethod
    # WHY Optional sem default: Pydantic field_validator (assinatura imposta).
    def _validate_horizon(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_DECISION_HORIZONS:
            raise ValueError(f"horizon inválido: {v!r}; aceitos: {sorted(VALID_DECISION_HORIZONS)}")
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
