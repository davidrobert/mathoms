"""Tests do `serialize_to_e3_legacy_format` propagando account_number + titulares (ADR-226 PR2)."""

from datetime import date
from decimal import Decimal

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money, Transaction
from pipeline.domain.services.e3_serialization import serialize_to_e3_legacy_format


def _stmt_with_account(account_number_norm: str | None) -> BankStatement:
    return BankStatement(
        institution="itau",
        member_key="david",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        currency="BRL",
        transactions=[
            Transaction(
                date=date(2026, 1, 15),
                description="Tx 1",
                amount=Money(amount=Decimal("100"), currency="BRL"),
            )
        ],
        account_number_norm=account_number_norm,
    )


def test_serializer_populates_account_number_and_titulares() -> None:
    stmt = _stmt_with_account("123456")
    result = serialize_to_e3_legacy_format(stmt, sources=["itau-0.pdf"])
    assert result["account_number"] == "123456"
    assert result["titular"] == "david"
    assert result["titulares"] == ["david"]


def test_serializer_propagates_account_number_to_transactions() -> None:
    stmt = _stmt_with_account("789012")
    result = serialize_to_e3_legacy_format(stmt, sources=["itau-0.pdf"])
    assert result["transacoes"][0]["account_number"] == "789012"


def test_serializer_omits_account_number_in_tx_when_statement_lacks_it() -> None:
    stmt = _stmt_with_account(None)
    result = serialize_to_e3_legacy_format(stmt, sources=["itau-0.pdf"])
    assert result["account_number"] is None
    assert "account_number" not in result["transacoes"][0]


def test_serializer_titulares_empty_when_no_member() -> None:
    stmt = BankStatement(
        institution="itau",
        member_key=None,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        currency="BRL",
    )
    result = serialize_to_e3_legacy_format(stmt, sources=["itau-0.pdf"])
    assert result["titulares"] == []
