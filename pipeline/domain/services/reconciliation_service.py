"""ReconciliationService — lógica pura de reconciliação (Fase 6 · R9/ISP).

Recebe :class:`ReconciliationConfig` (não ``StageConfig``). Permite testes
com fixture de 3 linhas em vez de mock completo de StageConfig.

Responsabilidades (espelha ``scripts/reconcile_transactions.py``):
- Agrupar ``BankStatement`` por (instituição, membro, moeda).
- Remover duplicatas exatas e fuzzy (±``tolerance_days``, ±``tolerance_amount``).
- Marcar transferências internas (crédito+débito mesmo valor, datas próximas).

A implementação é **minimalista** — serve como foundation. Lógica avançada de
validação de continuidade de saldo, detecção de transferências entre contas,
etc., é acrescentada quando E3 passar para Caminho B completo.

Hierarquia de fontes (ADR-146 · A7.6 rules-as-code)
====================================================

Quando duas fontes reportam a mesma transação (por exemplo: extrato +
fatura de cartão registrando o mesmo pagamento intermediado), a regra
canônica de tie-breaking está em
:mod:`pipeline.domain.services.source_tier`:

  1. Tier menor vence — TIER_LLM_STATEMENT (1) > TIER_REGEX_STATEMENT
     (2) > TIER_CARD_INVOICE (3) > TIER_APP_SCREENSHOT (4) >
     TIER_EDITORIAL (5).
  2. Mesmo tier → timestamp da extração mais recente vence (estável e
     idempotente entre reruns).

Override workspace-específico via ``BankAccount.source_tier``: NULL =
usar default Mathoms, não-NULL = força tier per-account.

A integração ``ReconciliationService.is_duplicate`` × source_tier é
**débito técnico aceito** desta lane — hoje o dedup ignora tier (todos
caem no path "extrato" tier 2). Quando ``ResolvedBankAccount.tier`` for
plumbado, a regra de prioridade fica explícita aqui. Para o "porquê":
ver ADR-146.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money, Transaction


def _tx_cents(tx: Transaction) -> int:
    """Cents (int) de uma tx — ``amount`` já é Decimal quantizado (ADR-090)."""
    return int((tx.amount.amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


def _cross_source(a: Transaction, b: Transaction) -> bool:
    """True se as duas tx vêm de ``source_document`` distintos (não-vazios)."""
    sa, sb = (a.source_document or ""), (b.source_document or "")
    return bool(sa) and bool(sb) and sa != sb


def _reconciled_copy(stmt: BankStatement, transactions: list[Transaction]) -> BankStatement:
    """Cópia de ``stmt`` com a lista de transações dedup-ada (não muta o original)."""
    # Construtor campo-a-campo: campo novo em BankStatement NÃO chega aqui sozinho —
    # é como `account_number_*` se perde (gate em
    # test_cross_document_collapser::test_reconcile_preserva_todo_campo_de_identidade).
    return BankStatement(
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
        extraction_method=stmt.extraction_method,
    )


@dataclass(frozen=True)
class DedupRemoval:
    """Remoção de tx declarada por canal (ADR-347). PR1 captura fatos (count, valor
    cents, cross_source_count = removidos com par-sobrevivente de fonte distinta); a
    política de needs_review para remoção não-provada é PR2 (measure-then-emit)."""

    canal: str  # "intra_statement_dedup" | "cross_file_dedup"
    count: int
    valor_cents: int
    cross_source_count: int
    source: str | None = None  # source_document do statement (intra); None p/ cross (merge)


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
        return self.reconcile_with_report(statements)[0]

    def reconcile_with_report(
        self, statements: Iterable[BankStatement]
    ) -> tuple[list[BankStatement], list[DedupRemoval]]:
        """Como :meth:`reconcile`, mais as remoções de dedup **intra-statement**
        declaradas por canal (ADR-347). O caller (adapter) soma a partição
        ``cross_file_dedup`` do merge."""
        groups: dict[tuple[str, str | None, str], list[BankStatement]] = {}
        for stmt in statements:
            key = (stmt.institution, stmt.member_key, stmt.currency)
            groups.setdefault(key, []).append(stmt)

        out: list[BankStatement] = []
        removals: list[DedupRemoval] = []
        for bundle in groups.values():
            reconciled, group_removals = self._reconcile_group_report(bundle)
            out.extend(reconciled)
            removals.extend(group_removals)
        return out, removals

    def find_duplicates(self, transactions: list[Transaction]) -> list[tuple[int, int]]:
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

    def _reconcile_group(self, stmts: list[BankStatement]) -> list[BankStatement]:
        return self._reconcile_group_report(stmts)[0]

    def _reconcile_group_report(
        self, stmts: list[BankStatement]
    ) -> tuple[list[BankStatement], list[DedupRemoval]]:
        reconciled: list[BankStatement] = []
        removals: list[DedupRemoval] = []
        for stmt in stmts:
            kept, count, valor_cents, cross = self.dedup_report(stmt.transactions)
            reconciled.append(_reconciled_copy(stmt, kept))
            if count:
                removals.append(
                    DedupRemoval(
                        "intra_statement_dedup", count, valor_cents, cross, stmt.source_document
                    )
                )
        return reconciled, removals

    def _dedup(self, transactions: list[Transaction]) -> list[Transaction]:
        return self.dedup_report(transactions)[0]

    def _duplicate_indices(
        self, transactions: list[Transaction]
    ) -> tuple[set[int], dict[int, int]]:
        """Índices removidos + o índice do sobrevivente que casou cada um."""
        survivor: dict[int, int] = {}
        dropped: set[int] = set()
        for i in range(len(transactions)):
            if i in dropped:
                continue
            for j in range(i + 1, len(transactions)):
                if j not in dropped and self.is_duplicate(transactions[i], transactions[j]):
                    dropped.add(j)
                    survivor[j] = i
        return dropped, survivor

    def dedup_report(
        self, transactions: list[Transaction]
    ) -> tuple[list[Transaction], int, int, int]:
        """Dedup + fatos por canal (ADR-347): ``(kept, count, valor_cents, cross_source_count)``."""
        dropped, survivor = self._duplicate_indices(transactions)
        kept = [t for i, t in enumerate(transactions) if i not in dropped]
        valor_cents = sum(_tx_cents(transactions[j]) for j in dropped)
        cross = sum(1 for j in dropped if _cross_source(transactions[j], transactions[survivor[j]]))
        return kept, len(dropped), valor_cents, cross
