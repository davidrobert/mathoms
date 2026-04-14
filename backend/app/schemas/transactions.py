"""Pydantic schemas for Transaction endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TransactionItem(BaseModel):
    data: str
    descricao: str
    valor: float
    banco: str
    categoria: str
    origem: Optional[str] = None
    tipo_conta: Optional[str] = None
    titular: Optional[str] = None
    moeda: Optional[str] = None
    transaction_hash: str
    is_overridden: bool = False


class TransactionSummary(BaseModel):
    total_receitas: float
    total_despesas: float
    saldo: float
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
