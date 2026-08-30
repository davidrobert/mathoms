"""Vocabulário de chave e proveniência compartilhado pelas passadas cross-documento.

Extraído de `cross_document_collapser` quando a passada de proximidade
([[A40.l102]]) virou módulo próprio: as duas precisam chavear a row do MESMO
jeito, e importar uma da outra fecharia ciclo. Manter uma cópia em cada lado é o
defeito que o `keep_split` desta lane já pagou — duas derivações da mesma
fórmula, uma delas atualizada.

Puro, sem I/O.
"""

from __future__ import annotations

from typing import Iterable

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Transaction
from pipeline.domain.services._tx_identity import (
    decimal_cents,
    derive_direction,
    normalize_banco,
    normalize_descricao,
    normalize_tipo_conta,
    normalize_titular,
)

__all__ = [
    "PROVENANCE_FIELDS",
    "collapse_key",
    "field_values",
    "provenance",
]

PROVENANCE_FIELDS: tuple[str, str, str] = ("banco", "titular", "tipo_conta")


def provenance(stmt: BankStatement) -> tuple[str, str, str]:
    """Tripla normalizada — MESMOS normalizadores do hash K4 e do detector da l1."""
    return (
        normalize_banco(stmt.institution),
        normalize_titular(stmt.member_key),
        normalize_tipo_conta(stmt.account_type),
    )


def _direction(tx: Transaction, stmt: BankStatement) -> str:
    return derive_direction(
        tipo=None, valor=float(tx.amount.amount), tipo_conta=stmt.account_type or ""
    )


def collapse_key(tx: Transaction, stmt: BankStatement) -> tuple:
    """Chave provenance-free day-exact — idêntica à do detector da [[A40.l1]]."""
    return (
        tx.date.isoformat(),
        decimal_cents(tx.amount.amount),
        (tx.amount.currency or "").strip().upper(),
        _direction(tx, stmt),
        normalize_descricao(tx.description),
    )


def field_values(provenances: Iterable[tuple[str, str, str]], name: str) -> frozenset[str]:
    """Valores de um campo de proveniência entre as pernas — nomes, nunca PII no trace."""
    idx = PROVENANCE_FIELDS.index(name)
    return frozenset(p[idx] for p in provenances)
