"""Tests do `serialize_to_e3_legacy_format` propagando account_number + titulares (ADR-226 PR2)."""

from dataclasses import fields
from datetime import date
from decimal import Decimal

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Money, Transaction
from pipeline.domain.services.e3_serialization import serialize_to_e3_legacy_format
from pipeline.domain.services.e3_statement_merge import merge_group_statements
from pipeline.domain.services.reconciliation_service import (
    ReconciliationConfig,
    ReconciliationService,
)


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


# =============================================================================
# O caminho real E2 → reconcile → payload (o serializer isolado sempre passou;
# o que estava quebrado era o reconcile zerando o campo antes de chegar aqui)
# =============================================================================


def _e2_dict(numero_conta: str | None, arquivo: str, dia: int) -> dict:
    return {
        "banco": "itau",
        "tipo": "extratoconta",
        "moeda": "BRL",
        "periodo_inicio": "2026-01-01",
        "periodo_fim": "2026-01-31",
        "documento_titular": "david",
        "numero_conta": numero_conta,
        "saldo_inicial": 100.0,
        "saldo_final": 150.0,
        "arquivo_origem": arquivo,
        "transacoes": [{"data": f"2026-01-{dia:02d}", "descricao": f"COMPRA {dia}", "valor": 50.0}],
    }


def _reconcile(stmts: list[BankStatement]) -> list[BankStatement]:
    return ReconciliationService(ReconciliationConfig()).reconcile(stmts)


def test_reconcile_preserves_account_number_into_payload() -> None:
    """ADR-226 PR2 ponta-a-ponta — regressão de 2026-08-05: ``_reconciled_copy``
    reconstruía campo-a-campo e o payload saía com ``account_number: None`` em
    todo run do E3."""
    entrada = BankStatement.from_e2_dict(_e2_dict("1234-5", "extrato.pdf", 10))
    (saida,) = _reconcile([entrada])

    assert (saida.account_number_raw, saida.account_number_norm) == ("1234-5", "12345")
    payload = serialize_to_e3_legacy_format(saida, sources=["extrato.pdf"])
    assert payload["account_number"] == "12345"
    assert payload["transacoes"][0]["account_number"] == "12345"


def test_reconcile_preserves_every_field_but_transactions() -> None:
    """Guarda de classe: qualquer campo novo em ``BankStatement`` sobrevive ao
    reconcile sem que alguém tenha de lembrar de editar ``_reconciled_copy``."""
    entrada = BankStatement.from_e2_dict(_e2_dict("1234-5", "extrato.pdf", 10))
    (saida,) = _reconcile([entrada])

    perdidos = [
        f.name
        for f in fields(BankStatement)
        if f.name != "transactions" and getattr(entrada, f.name) != getattr(saida, f.name)
    ]
    assert perdidos == []


def test_merge_keeps_account_number_when_group_has_a_single_one() -> None:
    stmts = _reconcile(
        [
            BankStatement.from_e2_dict(_e2_dict("1234-5", "extrato_a.pdf", 10)),
            BankStatement.from_e2_dict(_e2_dict("1234-5", "extrato_b.pdf", 20)),
        ]
    )
    merged = merge_group_statements(stmts, [t for s in stmts for t in s.transactions])

    assert merged.account_number_norm == "12345"
    assert merged.account_number_raw == "1234-5"


def test_merge_drops_account_number_when_group_mixes_accounts() -> None:
    """O ``output_key`` do merge não tem eixo de conta nem de membro: duas contas
    distintas do mesmo banco/tipo/moeda/período caem no mesmo artefato. Herdar o
    número do primeiro afirmaria identidade que o grupo não tem."""
    stmts = _reconcile(
        [
            BankStatement.from_e2_dict(_e2_dict("1234-5", "extrato_a.pdf", 10)),
            BankStatement.from_e2_dict(_e2_dict("9999-1", "extrato_b.pdf", 20)),
        ]
    )
    merged = merge_group_statements(stmts, [t for s in stmts for t in s.transactions])

    assert merged.account_number_norm is None
    assert merged.account_number_raw is None


def test_merge_preserves_metadata_of_the_first_statement() -> None:
    """O merge só deve divergir do primeiro nos campos que ele redefine —
    ``merge_group_statements`` usa ``replace`` para não zerar campo novo."""
    stmts = _reconcile(
        [
            BankStatement.from_e2_dict(_e2_dict("1234-5", "extrato_a.pdf", 10)),
            BankStatement.from_e2_dict(_e2_dict("1234-5", "extrato_b.pdf", 20)),
        ]
    )
    merged = merge_group_statements(stmts, [t for s in stmts for t in s.transactions])

    redefinidos = {"transactions", "source_document", "notes", "closing_balance"}
    divergentes = {
        f.name
        for f in fields(BankStatement)
        if getattr(stmts[0], f.name) != getattr(merged, f.name)
    }
    assert divergentes <= redefinidos
