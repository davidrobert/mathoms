"""Tests — ``e3_serialization`` (Fase 6 · Sessão A2).

Cobre paridade com ``scripts/e3_reconcile.generate_output_filename`` (linha 932)
e o schema E3 oficial (``config/schemas/e3_reconciled.schema.json``).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models import (  # noqa: E402
    BankCanonicalizer,
    BankStatement,
    Money,
    Transaction,
)
from pipeline.domain.services.e3_serialization import (  # noqa: E402
    generate_legacy_artifact_key,
    generate_legacy_filename,
    serialize_to_e3_legacy_format,
)


def _stmt(
    *,
    institution: str = "Itaú",
    account_type: str | None = "extratoconta",
    currency: str = "BRL",
    member_key: str | None = "david",
    period_start: date = date(2026, 1, 1),
    period_end: date = date(2026, 1, 31),
    opening: str | None = "1000.00",
    closing: str | None = "870.00",
    transactions: list[Transaction] | None = None,
) -> BankStatement:
    return BankStatement(
        institution=institution,
        member_key=member_key,
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        transactions=list(transactions or []),
        opening_balance=Money.of(opening, currency) if opening is not None else None,
        closing_balance=Money.of(closing, currency) if closing is not None else None,
        account_type=account_type,
    )


# =============================================================================
# generate_legacy_filename
# =============================================================================


class TestGenerateLegacyFilename:
    def test_conta_includes_currency(self):
        stmt = _stmt(
            institution="Itaú",
            account_type="extratoconta",
            currency="BRL",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        )

        # Sem canonicalizer: fallback lower().replace(" ", "") → "itaú"
        # (preserva acento — paridade com legado).
        assert (
            generate_legacy_filename(stmt)
            == "itaú_extratoconta_BRL_202601_202603-3_reconciled.json"
        )

    def test_fatura_excludes_currency(self):
        stmt = _stmt(
            institution="Nubank",
            account_type="faturacarbon",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
        )

        assert (
            generate_legacy_filename(stmt) == "nubank_faturacarbon_202604_202604-3_reconciled.json"
        )

    def test_uses_canonicalizer_when_provided(self):
        canon = BankCanonicalizer.from_institutions({"banco_canonical": {"itau": "Itaú"}})
        stmt = _stmt(
            institution="Itaú",
            account_type="extratoconta",
            currency="BRL",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )

        # Canonicalizer mapeia "Itaú" → "itau" (sem acento).
        assert (
            generate_legacy_filename(stmt, canonicalizer=canon)
            == "itau_extratoconta_BRL_202601_202601-3_reconciled.json"
        )

    def test_canonicalizer_strips_spaces_in_bank_name(self):
        canon = BankCanonicalizer.from_institutions({"banco_canonical": {"c6bank": "C6 Bank"}})
        stmt = _stmt(
            institution="C6 Bank",
            account_type="extratoconta",
            currency="BRL",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 6, 30),
        )

        assert (
            generate_legacy_filename(stmt, canonicalizer=canon)
            == "c6bank_extratoconta_BRL_202601_202606-3_reconciled.json"
        )

    def test_default_account_type_when_none(self):
        stmt = _stmt(account_type=None)

        assert "extrato" in generate_legacy_filename(stmt)

    def test_artifact_key_drops_suffix(self):
        stmt = _stmt(
            institution="itau",
            account_type="extratoconta",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )

        key = generate_legacy_artifact_key(stmt)

        assert key == "itau_extratoconta_BRL_202601_202601"
        assert not key.endswith("-3_reconciled.json")


# =============================================================================
# serialize_to_e3_legacy_format
# =============================================================================


class TestSerialize:
    def test_produces_required_schema_fields(self):
        stmt = _stmt()

        out = serialize_to_e3_legacy_format(stmt, sources=["src1.json"], duplicates_removed=0)

        # Campos obrigatórios do schema (e3_reconciled.schema.json)
        for field in (
            "banco",
            "tipo_conta",
            "moeda",
            "periodo_cobertura",
            "saldo_inicial",
            "saldo_inicial_unknown",
            "saldo_final",
            "saldo_final_unknown",
            "fontes",
            "transacoes_total",
            "transacoes_duplicadas_removidas",
            "transacoes",
        ):
            assert field in out, f"missing required field: {field}"

    def test_periodo_cobertura_uses_iso_dates(self):
        stmt = _stmt(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))

        out = serialize_to_e3_legacy_format(stmt, sources=[])

        assert out["periodo_cobertura"] == {
            "inicio": "2026-01-01",
            "fim": "2026-01-31",
        }

    def test_saldos_present_marks_unknown_false(self):
        stmt = _stmt(opening="1000.00", closing="500.00")

        out = serialize_to_e3_legacy_format(stmt, sources=[])

        assert out["saldo_inicial"] == 1000.00
        assert out["saldo_inicial_unknown"] is False
        assert out["saldo_final"] == 500.00
        assert out["saldo_final_unknown"] is False

    def test_saldos_none_marks_unknown_true_and_uses_zero(self):
        stmt = _stmt(opening=None, closing=None)

        out = serialize_to_e3_legacy_format(stmt, sources=[])

        assert out["saldo_inicial"] == 0.0
        assert out["saldo_inicial_unknown"] is True
        assert out["saldo_final"] == 0.0
        assert out["saldo_final_unknown"] is True

    def test_fontes_preserves_order(self):
        stmt = _stmt()

        out = serialize_to_e3_legacy_format(stmt, sources=["b.json", "a.json", "c.json"])

        assert out["fontes"] == ["b.json", "a.json", "c.json"]

    def test_transacoes_total_matches_list_length(self):
        tx = [
            Transaction(date(2026, 1, 5), "MERCADO", Money.brl("-100")),
            Transaction(date(2026, 1, 10), "UBER", Money.brl("-30")),
        ]
        stmt = _stmt(transactions=tx)

        out = serialize_to_e3_legacy_format(stmt, sources=["s"], duplicates_removed=2)

        assert out["transacoes_total"] == 2
        assert out["transacoes_duplicadas_removidas"] == 2
        assert len(out["transacoes"]) == 2

    def test_transacao_preserves_iso_date_and_description(self):
        tx = [Transaction(date(2026, 1, 5), "MERCADO PAO", Money.brl("-100.50"))]
        stmt = _stmt(transactions=tx)

        out = serialize_to_e3_legacy_format(stmt, sources=[])

        assert out["transacoes"][0] == {
            "data": "2026-01-05",
            "descricao": "MERCADO PAO",
            "valor": -100.50,
        }

    def test_transacao_includes_optional_fields_when_present(self):
        tx = [
            Transaction(
                date=date(2026, 1, 5),
                description="X",
                amount=Money.brl("10"),
                category="receita_outro",
                member_key="ana",
                source_document="extrato.pdf",
            )
        ]
        stmt = _stmt(transactions=tx)

        out = serialize_to_e3_legacy_format(stmt, sources=[])

        assert out["transacoes"][0]["categoria"] == "receita_outro"
        assert out["transacoes"][0]["membro"] == "ana"
        assert out["transacoes"][0]["arquivo_origem"] == "extrato.pdf"

    def test_titular_fallback_to_member_key(self):
        stmt = _stmt(member_key="david")

        out = serialize_to_e3_legacy_format(stmt, sources=[])

        assert out["titular"] == "david"

    def test_titular_explicit_overrides_member_key(self):
        stmt = _stmt(member_key="david")

        out = serialize_to_e3_legacy_format(stmt, sources=[], titular="cartao_familia")

        assert out["titular"] == "cartao_familia"

    def test_moeda_uppercased(self):
        # Money requer currency cadastrada em uppercase. O serializer apenas
        # garante uppercase no output — evita bug se algum statement chegar
        # com currency mista.
        stmt = _stmt(currency="USD", opening=None, closing=None)
        # Força mutação para validar normalização downstream.
        stmt.currency = "usd"

        out = serialize_to_e3_legacy_format(stmt, sources=[])

        assert out["moeda"] == "USD"

    def test_account_type_propagates_to_tipo_conta(self):
        stmt = _stmt(account_type="faturacarbon")

        out = serialize_to_e3_legacy_format(stmt, sources=[])

        assert out["tipo_conta"] == "faturacarbon"
