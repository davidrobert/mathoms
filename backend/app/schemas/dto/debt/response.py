"""Response DTOs do agregado ``Debt`` — Decimal em string (ADR-090, nunca float)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

DebtTipo = Literal[
    "financiamento_imobiliario",
    "consignado",
    "cdc",
    "cartao_rotativo",
    "rotativo",
    "outro",
]

DebtSource = Literal[
    "baseline_irpf_migration",
    "user_declared",
    "open_banking_futuro",
]


class DebtResponse(BaseModel):
    """Debt persistido (com cents convertidos para BRL Decimal)."""

    id: str = Field(..., max_length=36)
    workspace_id: str = Field(..., max_length=36)
    family_member_id: Optional[str] = Field(None, max_length=36)
    property_id: Optional[str] = Field(None, max_length=36)
    tipo: DebtTipo
    descricao: Optional[str] = None
    saldo_devedor_brl: Decimal = Field(..., ge=0)
    parcela_mensal_brl: Optional[Decimal] = Field(None, ge=0)
    taxa_juros_aa: Optional[Decimal] = None
    prazo_meses_restantes: Optional[int] = None
    data_contratacao: Optional[date] = None
    source: DebtSource
    migration_source_key: Optional[str] = None
    needs_review: bool
    percentual_atribuicao_imovel: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
