"""Pydantic schemas for Transaction endpoints.

Valores monetários (`valor`, `total_receitas`, `total_despesas`, `saldo`)
usam ``MoneyBRL`` (ADR-090) — Decimal em memória, number no JSON.
Campo ``moeda`` distingue transações USD no streaming, mas interno
usa MoneyBRL para precisão uniforme (ADR-090 aplica a qualquer money,
a semântica da moeda fica no label).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.app.schemas.money import MoneyBRL


class TransactionItem(BaseModel):
    data: str
    descricao: str
    valor: MoneyBRL
    banco: str
    categoria: str
    origem: Optional[str] = None
    tipo_conta: Optional[str] = None
    titular: Optional[str] = None
    moeda: Optional[str] = None
    transaction_hash: str
    is_overridden: bool = False


class TransactionSummary(BaseModel):
    total_receitas: MoneyBRL
    total_despesas: MoneyBRL
    saldo: MoneyBRL
    count: int
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None


class TransactionListResponse(BaseModel):
    transactions: list[TransactionItem]
    total: int
    page: int
    page_size: int
    summary: TransactionSummary


class TransactionOverrideRequest(BaseModel):
    new_category: str
    notes: Optional[str] = None


class TransactionOverrideResponse(BaseModel):
    id: str
    transaction_hash: str
    original_category: str
    new_category: str
    notes: Optional[str] = None
    reviewed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
