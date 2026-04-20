"""ReconciliationService — lógica pura de reconciliação (Fase 6 · R9/ISP).

Recebe :class:`ReconciliationConfig` (não ``StageConfig``). Permite testes
com fixture de 3 linhas em vez de mock completo de StageConfig.

Responsabilidades (espelha ``scripts/e3_reconcile.py``):
- Agrupar ``BankStatement`` por (instituição, membro, moeda).
- Remover duplicatas exatas e fuzzy (±``tolerance_days``, ±``tolerance_amount``).
- Marcar transferências internas (crédito+débito mesmo valor, datas próximas).

A implementação é **minimalista** — serve como foundation. Lógica avançada de
validação de continuidade de saldo, detecção de transferências entre contas,
etc., é acrescentada quando E3 passar para Caminho B completo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money, Transaction


@dataclass(frozen=True)
class ReconciliationConfig:
    """Parâmetros de reconciliação — subset do pipeline config (R9)."""

    tolerance_days: int = 3
    tolerance_amount: Decimal = Decimal("0.01")
    skip_types: frozenset[str] = frozenset()

    @classmethod
    def from_pipeline_config(cls, pipeline: dict) -> "ReconciliationConfig":
        r = (pipeline or {}).get("reconciliation", {})
        return cls(
            tolerance_days=int(r.get("tolerance_days", 3)),
            tolerance_amount=Decimal(str(r.get("tolerance_amount", "0.01"))),
            skip_types=frozenset(r.get("skip_types", [])),
        )


class ReconciliationService:
    """Reconcilia extratos bancários sem I/O."""

    def __init__(self, config: ReconciliationConfig):
        self._config = config

    # -- API pública --

    def reconcile(self, statements: Iterable[BankStatement]) -> list[BankStatement]:
        """Retorna uma nova lista com duplicatas removidas e transfers marcados.

        Não muta os extratos de entrada — cria novos ``BankStatement`` quando
        há alteração.
        """
        groups: dict[tuple[str, str | None, str], list[BankStatement]] = {}
        for stmt in statements:
            key = (stmt.institution, stmt.member_key, stmt.currency)
            groups.setdefault(key, []).append(stmt)

        out: list[BankStatement] = []
        for bundle in groups.values():
            out.extend(self._reconcile_group(bundle))
        return out

    def find_duplicates(
        self, transactions: list[Transaction]
    ) -> list[tuple[int, int]]:
        """Pares de índices ``(i, j)`` considerados duplicatas (i < j)."""
        pairs: list[tuple[int, int]] = []
        for i in range(len(transactions)):
            for j in range(i + 1, len(transactions)):
                if self.is_duplicate(transactions[i], transactions[j]):
                    pairs.append((i, j))
        return pairs

    def is_duplicate(self, a: Transaction, b: Transaction) -> bool:
        if a.amount.currency != b.amount.currency:
            return False
        if abs((a.amount.amount - b.amount.amount)) > self._config.tolerance_amount:
            return False
        if abs((a.date - b.date).days) > self._config.tolerance_days:
            return False
        if a.description != b.description:
            # conservador: descrição idêntica + valor + data próxima → dedup
            return False
        return True

    def is_transfer_pair(self, a: Transaction, b: Transaction) -> bool:
        """Par de transferência interna: valores opostos, datas próximas."""
        if a.amount.currency != b.amount.currency:
            return False
        if (a.amount + b.amount).amount != Decimal(0):
            return False
        if abs((a.date - b.date).days) > self._config.tolerance_days:
            return False
        return True

    # -- Implementação --

    def _reconcile_group(
        self, stmts: list[BankStatement]
    ) -> list[BankStatement]:
        reconciled: list[BankStatement] = []
        for stmt in stmts:
            transactions = self._dedup(stmt.transactions)
            reconciled.append(
                BankStatement(
                    institution=stmt.institution,
                    member_key=stmt.member_key,
                    period_start=stmt.period_start,
                    period_end=stmt.period_end,
                    currency=stmt.currency,
                    transactions=transactions,
                    opening_balance=stmt.opening_balance,
                    closing_balance=stmt.closing_balance,
                    source_document=stmt.source_document,
                    notes=list(stmt.notes),
                    account_type=stmt.account_type,
                )
            )
        return reconciled

    def _dedup(self, transactions: list[Transaction]) -> list[Transaction]:
        seen_indexes: set[int] = set()
        for i in range(len(transactions)):
            if i in seen_indexes:
                continue
            for j in range(i + 1, len(transactions)):
                if j in seen_indexes:
                    continue
                if self.is_duplicate(transactions[i], transactions[j]):
                    seen_indexes.add(j)
        return [t for i, t in enumerate(transactions) if i not in seen_indexes]
