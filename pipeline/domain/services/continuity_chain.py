"""Identidade de conta e particionamento em cadeias de continuidade (ADR-310).

"Mesma conta" tem uma única definição no domínio: ``ContinuityAccountKey``
deriva da ``AccountKey`` canônica do ``AccountGrouper`` (banco + tipo + moeda)
+ ``member_key``/``account_number_norm`` (ADR-226). ``_partition_chains`` é o
helper compartilhado por ``SaldoContinuityValidator`` E ``TemporalGapDetector``
— uma única definição de "quais statements formam uma cadeia".

Emenda ADR-310 (2026-07-08, A35.l1): ``account_number_norm`` vem da extração
(``document.py:158``) e falha em silêncio quando o parser não casa o número;
dois extratos da MESMA conta — um com número, outro sem — viravam cadeias
separadas e o gap genuíno entre eles sumia (issue #860). O fallback intra-run
(Tier 2) coalesce os sem-número na cadeia numerada quando o grupo tem um único
número distinto, sempre com sinal auditável ``SaldoChainMemberInferred``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from pipeline.domain.models.document import BankStatement
from pipeline.domain.services.account_grouper import AccountGrouper, AccountKey

# =============================================================================
# Chave de agregação por conta (ADR-310)
# =============================================================================


@dataclass(frozen=True)
class ContinuityAccountKey:
    """Identidade de conta na cadeia de continuidade (ADR-310): ``account``
    é a ``AccountKey`` canônica do ``AccountGrouper`` — "mesma conta" tem
    uma única definição no domínio — e ``member``/``account_number``
    (``account_number_norm``, ADR-226) são discriminadores adicionais que
    a cadeia de saldo exige."""

    account: AccountKey
    member: str | None
    account_number: str | None

    @property
    def bank(self) -> str:
        return self.account.bank

    @property
    def account_type(self) -> str:
        return self.account.account_type

    @property
    def currency(self) -> str | None:
        return self.account.currency

    @property
    def is_fatura(self) -> bool:
        return self.account.is_fatura

    def describe(self) -> str:
        """Identificação humana da conta — sem ``account_number`` (dado
        sensível não vai para mensagem/ReviewReason; os source documents
        já identificam o par ofensor)."""
        tipo = self.account_type or "-"
        return f"{self.bank}/{tipo}/{self.member or '-'}/{self.currency or '-'}"


def chain_key(grouper: AccountGrouper, stmt: BankStatement) -> ContinuityAccountKey:
    account = grouper.key_for_statement(stmt)
    if account is None:
        # Sem tipo/banco determinável — statement permanece na validação,
        # agrupado por (banco, tipo vazio, moeda) como o legado fazia.
        account = AccountKey(
            bank=stmt.institution.lower(),
            account_type=(stmt.account_type or "").strip(),
            currency=stmt.currency.upper(),
        )
    return ContinuityAccountKey(
        account=account,
        member=stmt.member_key,
        account_number=stmt.account_number_norm,
    )


def sort_key(stmt: BankStatement) -> tuple:
    """Ordenação determinística (ADR-310): nunca ordem de inserção/hash."""
    return (stmt.period_start, stmt.period_end, stmt.source_document or "")


# =============================================================================
# Sinais de auditoria da partição (dataclasses tipadas, ADR-097 D1)
# =============================================================================


@dataclass(frozen=True)
class FaturaExcludedFromSaldoChain:
    """Sinal tipado (ADR-310): statement classificado como fatura ficou fora
    da cadeia de continuidade de saldo — toda exclusão é auditável; conta
    legítima erroneamente classificada como fatura aparece aqui (com seu
    ``source_document``), nunca some da validação em silêncio."""

    source_document: str | None
    bank: str
    account_type: str

    def format(self) -> str:
        return (
            f"saldo-continuity: fatura fora da cadeia {self.bank}/{self.account_type} "
            f"src={self.source_document or '?'} (ADR-310)"
        )


@dataclass(frozen=True)
class SaldoChainMemberInferred:
    """Sinal tipado (emenda ADR-310 2026-07-08): um statement sem
    ``account_number_norm`` foi coalescido na cadeia numerada da mesma conta
    (Tier 2 — grupo com exatamente um número distinto). Número ausente tem
    duas causas indistinguíveis (banco não emite × parser regrediu); o sinal
    torna a inferência visível — nunca costura em silêncio. Espelha
    ``FaturaExcludedFromSaldoChain``: sem ``account_number`` cru (dado
    sensível; ``describe()`` já omite)."""

    source_document: str | None
    account: ContinuityAccountKey

    def format(self) -> str:
        return (
            f"saldo-continuity: membro sem numero coalescido na cadeia "
            f"{self.account.describe()} src={self.source_document or '?'} "
            f"(ADR-310 emenda 2026-07-08)"
        )


# =============================================================================
# Particionamento em cadeias (helper compartilhado — emenda ADR-310)
# =============================================================================


@dataclass(frozen=True)
class ChainPartition:
    """Statements agrupados por cadeia de conta, com os sinais de auditoria da
    partição. Consumido por ``SaldoContinuityValidator`` E ``TemporalGapDetector``
    (uma única definição de "quais statements formam uma cadeia")."""

    chains: dict[ContinuityAccountKey, list[BankStatement]]
    excluded_faturas: tuple[FaturaExcludedFromSaldoChain, ...]
    inferred_members: tuple[SaldoChainMemberInferred, ...]


def _collapse_group(key: ContinuityAccountKey) -> tuple:
    """Grupo `(banco, membro, tipo, moeda)` — a chave da continuidade sem o
    eixo ``account_number`` (o único discriminador que a emenda relaxa)."""
    return (key.bank, key.member, key.account_type, key.currency)


def _sole_number(chains: dict[ContinuityAccountKey, list[BankStatement]]) -> str | None:
    """Único ``account_number`` não-nulo do grupo, ou ``None`` se 0 ou >= 2
    distintos (predicado set-based puro — determinismo ADR-111)."""
    numbers = {k.account_number for k in chains if k.account_number is not None}
    return next(iter(numbers)) if len(numbers) == 1 else None


def _survivor_key(group_key: tuple, number: str) -> ContinuityAccountKey:
    """Reconstrói a ``ContinuityAccountKey`` numerada canônica do grupo (o
    sobrevivente fixo da coalescência — nunca ``next(iter(...))`` sobre dict)."""
    bank, member, account_type, currency = group_key
    account = AccountKey(bank=bank, account_type=account_type, currency=currency)
    return ContinuityAccountKey(account=account, member=member, account_number=number)


def _merge_group(
    survivor: ContinuityAccountKey,
    keyed: dict[ContinuityAccountKey, list[BankStatement]],
    merged: dict[ContinuityAccountKey, list[BankStatement]],
) -> list[SaldoChainMemberInferred]:
    """Funde as sub-cadeias do grupo na cadeia numerada; retorna um sinal por
    statement sem número coalescido."""
    target = merged.setdefault(survivor, [])
    inferred: list[SaldoChainMemberInferred] = []
    for key, group in keyed.items():
        target.extend(group)
        if key.account_number is None:
            inferred += [SaldoChainMemberInferred(s.source_document, survivor) for s in group]
    return inferred


def _coalesce_accountless(
    chains: dict[ContinuityAccountKey, list[BankStatement]],
) -> tuple[dict[ContinuityAccountKey, list[BankStatement]], list[SaldoChainMemberInferred]]:
    """Emenda ADR-310 (Tier 2): dentro de cada grupo `(banco, membro, tipo,
    moeda)` com exatamente um número distinto, funde os statements sem número
    na cadeia numerada. Emite um sinal por statement coalescido — nunca em
    silêncio."""
    by_group: dict[tuple, dict[ContinuityAccountKey, list[BankStatement]]] = defaultdict(dict)
    for key, group in chains.items():
        by_group[_collapse_group(key)][key] = group

    merged: dict[ContinuityAccountKey, list[BankStatement]] = {}
    inferred: list[SaldoChainMemberInferred] = []
    for group_key, keyed in by_group.items():
        number = _sole_number(keyed)
        if number is None:
            merged.update(keyed)
            continue
        inferred += _merge_group(_survivor_key(group_key, number), keyed, merged)
    return merged, inferred


def partition_chains(
    grouper: AccountGrouper,
    statements: Iterable[BankStatement],
    *,
    exclude_faturas: bool,
) -> ChainPartition:
    """Particiona statements em cadeias de conta (emenda ADR-310). Statements
    sem número coalescem na cadeia numerada quando o grupo `(banco, membro,
    tipo, moeda)` tem um único número distinto (Tier 2). Faturas: saem da
    cadeia com sinal na continuidade de saldo (``exclude_faturas=True``) ou
    formam cadeia própria na detecção temporal (``False``) — coalescência é
    no-op para elas (sempre ``account_number=None``). Função pura — mesma
    entrada em qualquer ordem produz a mesma partição."""
    chains: dict[ContinuityAccountKey, list[BankStatement]] = defaultdict(list)
    excluded: list[FaturaExcludedFromSaldoChain] = []
    for s in statements:
        key = chain_key(grouper, s)
        if exclude_faturas and key.is_fatura:
            excluded.append(
                FaturaExcludedFromSaldoChain(s.source_document, key.bank, key.account_type)
            )
        else:
            chains[key].append(s)
    coalesced, inferred = _coalesce_accountless(dict(chains))
    inferred_sorted = tuple(
        sorted(inferred, key=lambda i: (i.account.describe(), i.source_document or ""))
    )
    return ChainPartition(coalesced, tuple(excluded), inferred_sorted)
