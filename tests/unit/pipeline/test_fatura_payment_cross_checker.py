"""ADR-350 PR1 (measure-only) — FaturaPaymentCrossChecker casa pagamento de fatura
("Inclusao de Pagamento") ↔ débito no extrato por (data±janela, cents). Emite
passou/faltando; NUNCA escala. Validado no corpus 5@5.com (17/18 passou)."""

from __future__ import annotations

from datetime import date

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money, Transaction
from pipeline.domain.services.fatura_payment_cross_checker import (
    FaturaCrossCheckConfig,
    FaturaPaymentCrossChecker,
    attach_cross_checksum,
    index_by_key,
)


def _tx(d: str, desc: str, valor: str) -> Transaction:
    return Transaction(date=date.fromisoformat(d), description=desc, amount=Money.of(valor, "BRL"))


def _stmt(account_type: str, txs: list[Transaction], member: str = "m1") -> BankStatement:
    return BankStatement(
        institution="C6Bank",
        member_key=member,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        currency="BRL",
        transactions=txs,
        account_type=account_type,
    )


_PAY = ("2026-01-10", "Inclusao de Pagamento", "-500.00")


def test_payment_matches_witness_debit_passou() -> None:
    fat = _stmt("faturacarbon", [_tx(*_PAY)])
    ext = _stmt("extratoconta", [_tx("2026-01-11", "PAGAMENTO FATURA", "-500.00")])
    res = FaturaPaymentCrossChecker().check([fat, ext])
    assert len(res) == 1
    assert res[0].status == "passou"
    assert res[0].payment_cents == 50000 and res[0].witness_debit_cents == 50000


def test_no_witness_faltando() -> None:
    fat = _stmt("faturacarbon", [_tx(*_PAY)])
    ext = _stmt("extratoconta", [_tx("2026-01-10", "OUTRA COISA", "-123.45")])
    res = FaturaPaymentCrossChecker().check([fat, ext])
    assert res[0].status == "faltando" and res[0].witness_debit_cents is None


def test_witness_outside_window_faltando() -> None:
    fat = _stmt("faturacarbon", [_tx(*_PAY)])
    ext = _stmt("extratoconta", [_tx("2026-01-20", "PAGAMENTO", "-500.00")])  # 10d > 5d
    res = FaturaPaymentCrossChecker(FaturaCrossCheckConfig(window_days=5)).check([fat, ext])
    assert res[0].status == "faltando"


def test_non_fatura_statements_ignored() -> None:
    ext = _stmt("extratoconta", [_tx(*_PAY)])  # "pagamento" num extrato não é fatura
    assert FaturaPaymentCrossChecker().check([ext]) == ()


def test_purity_no_mutation() -> None:
    fat = _stmt("faturacarbon", [_tx(*_PAY)])
    ext = _stmt("extratoconta", [_tx("2026-01-11", "PGTO", "-500.00")])
    FaturaPaymentCrossChecker().check([fat, ext])
    assert len(fat.transactions) == 1 and len(ext.transactions) == 1  # nada mutado


def test_attach_helper_sets_and_skips_payload_trace() -> None:
    fat = _stmt("faturacarbon", [_tx(*_PAY)])
    ext = _stmt("extratoconta", [_tx("2026-01-11", "PGTO", "-500.00")])
    results = FaturaPaymentCrossChecker().check([fat, ext])
    payload: dict = {}
    attach_cross_checksum(payload, fat, index_by_key(results))
    assert payload["fatura_cross_checksum"][0]["status"] == "passou"
    # sem cross-checker (map vazio) → no-op, não polui o payload.
    empty: dict = {}
    attach_cross_checksum(empty, fat, {})
    assert "fatura_cross_checksum" not in empty
