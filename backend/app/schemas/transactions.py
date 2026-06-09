"""Pydantic schemas for Transaction endpoints.

Valores monetários (`valor`, `total_receitas`, `total_despesas`, `saldo`)
usam ``MoneyBRL`` (ADR-090) — Decimal em memória, number no JSON.
Campo ``moeda`` distingue transações USD no streaming, mas interno
usa MoneyBRL para precisão uniforme (ADR-090 aplica a qualquer money,
a semântica da moeda fica no label).
"""

from datetime import datetime
from typing import Literal, Optional

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
    # ADR-282 read-path: ``credito``/``debito`` derivado do bucket E4
    # (receitas→credito, despesas→debito) — NÃO do sinal de ``valor`` (E4 grava
    # despesa com ``abs``, então sinal daria direction errada). Alimenta o hash
    # v2 do override via ``inputs_from_transaction_item``.
    tipo: Optional[str] = None
    # Identidade lógica (data|descricao|valor|banco|titular). Múltiplas
    # transações físicas idênticas (ex.: 2 lattes no mesmo dia) compartilham
    # este hash — propositalmente, pois TransactionOverride é unique por hash.
    transaction_hash: str
    # Identidade física estável por linha (`{hash}:{occurrence_idx}`). Usado
    # como chave de render no frontend; resolve colisão de keys quando hash
    # logical repete entre linhas distintas.
    row_id: str
    is_overridden: bool = False
    # ADR-186/188 (A12 P4) — origem do override; ``None`` quando não há.
    # UI mostra badge "Categorizada por regra" quando ``rule``.
    override_source: Optional[Literal["manual", "rule"]] = None


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
