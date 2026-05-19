"""Tests do propagation de ``account_number`` em BankStatement (ADR-226 PR2)."""

from datetime import date

from pipeline.domain.models.document import BankStatement


def test_from_e2_dict_normalizes_dirty_numero_conta() -> None:
    d = {
        "banco": "itau",
        "moeda": "BRL",
        "periodo_inicio": "2026-01-01",
        "periodo_fim": "2026-01-31",
        "numero_conta": "12.345-6",
        "transacoes": [],
    }
    stmt = BankStatement.from_e2_dict(d)
    assert stmt.account_number_raw == "12.345-6"
    assert stmt.account_number_norm == "123456"


def test_from_e2_dict_preserves_norm_when_already_populated() -> None:
    d = {
        "banco": "c6bank",
        "moeda": "BRL",
        "periodo_inicio": "2026-01-01",
        "periodo_fim": "2026-01-31",
        "numero_conta": "55.667-7",
        "numero_conta_norm": "556677",
        "transacoes": [],
    }
    stmt = BankStatement.from_e2_dict(d)
    assert stmt.account_number_norm == "556677"


def test_from_e2_dict_handles_missing_numero_conta() -> None:
    d = {
        "banco": "nubank",
        "moeda": "BRL",
        "periodo_inicio": "2026-01-01",
        "periodo_fim": "2026-01-31",
        "transacoes": [],
    }
    stmt = BankStatement.from_e2_dict(d)
    assert stmt.account_number_raw is None
    assert stmt.account_number_norm is None


def test_bank_statement_default_account_number_is_none() -> None:
    stmt = BankStatement(
        institution="itau",
        member_key="david",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        currency="BRL",
    )
    assert stmt.account_number_raw is None
    assert stmt.account_number_norm is None
