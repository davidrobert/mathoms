"""Checksum cross-source de fatura ([[ADR-350]]) — validador de domínio puro.

Faturas c6 carbon CSV não têm total impresso → sem checksum intra-artefato
([[ADR-342]] marca `fatura_checksum.status="faltando"`). A testemunha independente
é o **débito de pagamento no extrato de conta**: a linha "Inclusao de Pagamento"
da fatura casa por **(data ± janela, valor em cents)** com um débito no extrato
(validado no corpus: 17/18 casam exato; 1/18 sem testemunha no corpus).

Match por valor+data, NÃO por descrição — o débito de pagamento no extrato não
tem rótulo estável (ex.: não é "PGTO FAT CARTAO"). Measure-only ([[ADR-347]]): o
checker emite traço `{status: passou|faltando}`; NÃO escala `needs_review`
(política de gate + detecção de `mismatch`/Contrato B = PR2, após medir a taxa de
falso-positivo). Puro, sem I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pipeline.domain.models.document import BankStatement

# C6-only v1 ([[ADR-350]]): o discriminador do pagamento é C6-específico.
_FATURA_TYPES = frozenset({"faturacarbon"})
_ACCOUNT_TYPES = frozenset({"extratoconta", "extratocontabrl", "extratopoupanca"})
_PAYMENT_DESC = "inclusao de pagamento"


@dataclass(frozen=True)
class FaturaCrossCheckConfig:
    """Config tipada (ISP, [[ADR-089]]) — janela de casamento data↔débito em dias."""

    window_days: int = 5


@dataclass(frozen=True)
class FaturaCrossResult:
    """Traço PII-safe por pagamento de fatura (só cents/datas/códigos)."""

    institution: str | None
    member_key: str | None
    payment_date: str | None
    status: str  # "passou" | "faltando"
    payment_cents: int
    witness_debit_cents: int | None

    def to_trace_dict(self) -> dict:
        return {
            "status": self.status,
            "payment_cents": self.payment_cents,
            "witness_debit_cents": self.witness_debit_cents,
            "payment_date": self.payment_date,
        }


def _cents(amount) -> int:
    return round(abs(amount.to_float()) * 100)


def _result_key(institution, member_key, payment_date: str | None, payment_cents: int) -> tuple:
    return (institution, member_key, payment_date, payment_cents)


def index_by_key(results: tuple[FaturaCrossResult, ...]) -> dict:
    """Indexa resultados por (inst, membro, data, cents) — chave de casamento c/ o payload."""
    return {
        _result_key(r.institution, r.member_key, r.payment_date, r.payment_cents): r
        for r in results
    }


def _payment_key(merged_stmt, tx) -> tuple:
    return _result_key(
        merged_stmt.institution,
        merged_stmt.member_key,
        tx.date.isoformat() if tx.date else None,
        _cents(tx.amount),
    )


def attach_cross_checksum(payload: dict, merged_stmt, indexed: dict) -> None:
    """Anexa `fatura_cross_checksum` ([[ADR-350]], measure-only) ao payload de fatura
    (casa cada "Inclusao de Pagamento" ao resultado). No-op sem checker/pagamento."""
    if not indexed:
        return
    traces = []
    for tx in merged_stmt.transactions:
        if _PAYMENT_DESC not in (tx.description or "").lower():
            continue
        result = indexed.get(_payment_key(merged_stmt, tx))
        if result is not None:
            traces.append(result.to_trace_dict())
    if traces:
        payload["fatura_cross_checksum"] = traces


class FaturaPaymentCrossChecker:
    """Casa pagamento de fatura ↔ débito no extrato ([[ADR-350]], measure-only)."""

    def __init__(self, config: FaturaCrossCheckConfig | None = None) -> None:
        self._cfg = config or FaturaCrossCheckConfig()

    def check(self, statements: list[BankStatement]) -> tuple[FaturaCrossResult, ...]:
        debits = self._account_debits(statements)
        return tuple(
            self._check_payment(stmt, tx, debits)
            for stmt in statements
            if stmt.account_type in _FATURA_TYPES
            for tx in stmt.transactions
            if _PAYMENT_DESC in (tx.description or "").lower()
        )

    def _account_debits(self, statements: list[BankStatement]) -> list[tuple[date, int]]:
        """(data, cents) de todo débito (amount<0) em extratos de conta."""
        return [
            (tx.date, _cents(tx.amount))
            for stmt in statements
            if stmt.account_type in _ACCOUNT_TYPES
            for tx in stmt.transactions
            if tx.amount.to_float() < 0 and tx.date is not None
        ]

    def _check_payment(self, stmt: BankStatement, tx, debits) -> FaturaCrossResult:
        pcents = _cents(tx.amount)
        witness = self._witness(pcents, tx.date, debits)
        return FaturaCrossResult(
            institution=stmt.institution,
            member_key=stmt.member_key,
            payment_date=tx.date.isoformat() if tx.date else None,
            status="passou" if witness is not None else "faltando",
            payment_cents=pcents,
            witness_debit_cents=witness,
        )

    def _witness(self, pcents: int, pdate, debits: list[tuple[date, int]]) -> int | None:
        """Débito com cents EXATO dentro da janela; None se ausente do corpus."""
        for ddate, dcents in debits:
            if dcents == pcents and (
                pdate is None or abs((pdate - ddate).days) <= self._cfg.window_days
            ):
                return dcents
        return None
