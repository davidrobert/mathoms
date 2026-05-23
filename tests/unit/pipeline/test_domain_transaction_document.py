"""Tests — ``Transaction`` e ``BankStatement``/``InvestmentStatement`` (Fase 5.3-5.5)."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models import (  # noqa: E402
    BankStatement,
    BaselinePatrimonial,
    Investment,
    InvestmentStatement,
    Money,
    Transaction,
)


class TestTransactionBasics:
    def _tx(self, amount: str = "10.00", **kwargs):
        return Transaction(
            date=date(2026, 1, 15),
            description="MERCADO XYZ",
            amount=Money.brl(amount),
            **kwargs,
        )

    def test_frozen_cannot_mutate(self):
        t = self._tx()
        with pytest.raises(FrozenInstanceError):
            t.description = "x"  # type: ignore[misc]

    def test_with_category_returns_new_instance(self):
        t = self._tx(category=None)
        t2 = t.with_category("Alimentacao")
        assert t.category is None
        assert t2.category == "Alimentacao"
        assert t.amount == t2.amount

    def test_replace_is_explicit_api(self):
        t = self._tx()
        t2 = replace(t, category="Foo")
        assert t2.category == "Foo"

    def test_round_trip_dict(self):
        t = self._tx(amount="-25.50", category="Lazer", member_key="david")
        assert Transaction.from_dict(t.to_dict()) == t


class TestBankStatementAggregates:
    def _build(self) -> BankStatement:
        return BankStatement(
            institution="itau",
            member_key="david",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            currency="BRL",
            transactions=[
                Transaction(date(2026, 1, 2), "Salário", Money.brl("5000")),
                Transaction(date(2026, 1, 3), "Mercado", Money.brl("-300")),
                Transaction(date(2026, 1, 4), "Restaurante", Money.brl("-50.50")),
                Transaction(date(2026, 1, 10), "Devolução", Money.brl("20")),
            ],
            opening_balance=Money.brl("1000"),
            closing_balance=Money.brl("5669.50"),
        )

    def test_net_flow(self):
        stmt = self._build()
        assert stmt.net_flow == Money.brl("4669.50")

    def test_income_sums_positive(self):
        stmt = self._build()
        assert stmt.income == Money.brl("5020")

    def test_expenses_returned_positive(self):
        stmt = self._build()
        assert stmt.expenses == Money.brl("350.50")

    def test_round_trip_dict(self):
        stmt = self._build()
        d = stmt.to_dict()
        rebuilt = BankStatement.from_dict(d)
        assert rebuilt.institution == stmt.institution
        assert rebuilt.member_key == stmt.member_key
        assert rebuilt.currency == stmt.currency
        assert rebuilt.period_start == stmt.period_start
        assert rebuilt.period_end == stmt.period_end
        assert rebuilt.opening_balance == stmt.opening_balance
        assert rebuilt.closing_balance == stmt.closing_balance
        assert [t.description for t in rebuilt.transactions] == [
            "Salário",
            "Mercado",
            "Restaurante",
            "Devolução",
        ]


class TestCategoryHintPropagation:
    """ADR-242 — ``categoria_sugerida`` do LLM (E2-llm) precisa sobreviver ao
    reconciler para o classifier consumir em E4. Regression test contra o bug
    em que ``from_e2_dict`` descartava o campo e ADR-242 §D2 (skip
    ``info_fiscal_anual``) virava dead code em produção."""

    def test_from_e2_dict_preserves_category_hint(self):
        d = {
            "banco": "itau",
            "tipo": "informe_rendimentos",
            "moeda": "BRL",
            "periodo_inicio": "2025-01-01",
            "periodo_fim": "2025-12-31",
            "arquivo_origem": "informe.pdf",
            "transacoes": [
                {
                    "data": "2025-12-31",
                    "descricao": "Parcelas Pagas Crédito Imobiliário (ano 2025)",
                    "valor": -52429.06,
                    "categoria_sugerida": "info_fiscal_anual",
                }
            ],
        }
        stmt = BankStatement.from_e2_dict(d)
        assert stmt.transactions[0].category_hint == "info_fiscal_anual"

    def test_to_e2_dict_exports_category_hint(self):
        tx = Transaction(
            date=date(2025, 12, 31),
            description="Parcelas Pagas Crédito Imobiliário (ano 2025)",
            amount=Money.brl("-52429.06"),
            category_hint="info_fiscal_anual",
        )
        stmt = BankStatement(
            institution="itau",
            member_key="david",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            currency="BRL",
            transactions=[tx],
        )
        d = stmt.to_e2_dict()
        assert d["transacoes"][0]["categoria_sugerida"] == "info_fiscal_anual"

    def test_to_e2_dict_omits_hint_when_none(self):
        """Transação determinística (parser de banco, sem LLM) NÃO ganha o campo."""
        tx = Transaction(
            date=date(2025, 12, 31),
            description="MERCADO X",
            amount=Money.brl("-100.00"),
        )
        stmt = BankStatement(
            institution="itau",
            member_key="david",
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            currency="BRL",
            transactions=[tx],
        )
        d = stmt.to_e2_dict()
        assert "categoria_sugerida" not in d["transacoes"][0]

    def test_round_trip_e2_dict_preserves_hint(self):
        original = {
            "banco": "itau",
            "tipo": "informe_rendimentos",
            "moeda": "BRL",
            "periodo_inicio": "2025-01-01",
            "periodo_fim": "2025-12-31",
            "arquivo_origem": "informe.pdf",
            "transacoes": [
                {
                    "data": "2025-12-31",
                    "descricao": "x",
                    "valor": -1.0,
                    "categoria_sugerida": "info_fiscal_anual",
                }
            ],
        }
        rebuilt = BankStatement.from_e2_dict(original).to_e2_dict()
        assert rebuilt["transacoes"][0]["categoria_sugerida"] == "info_fiscal_anual"


class TestInvestmentStatement:
    def test_total_value_sums(self):
        stmt = InvestmentStatement(
            institution="btgpactual",
            member_key="david",
            currency="BRL",
            investments=[
                Investment("CDB", "btg", "CDB 2027", Money.brl("10000")),
                Investment("LCI", "btg", "LCI 2028", Money.brl("5000.50")),
            ],
        )
        assert stmt.total_value == Money.brl("15000.50")

    def test_round_trip_dict(self):
        inv = Investment("FII", "xpi", "KNRI11", Money.brl("1500"))
        stmt = InvestmentStatement(
            institution="xpi",
            member_key="elena",
            currency="BRL",
            investments=[inv],
        )
        rebuilt = InvestmentStatement.from_dict(stmt.to_dict())
        assert rebuilt.total_value == Money.brl("1500")


class TestBaselinePatrimonial:
    def test_round_trip(self):
        bp = BaselinePatrimonial(
            total_brl=Money.brl("100000"),
            members={"david": Money.brl("60000"), "elena": Money.brl("40000")},
            reference_date=date(2026, 1, 1),
        )
        rebuilt = BaselinePatrimonial.from_dict(bp.to_dict())
        assert rebuilt.total_brl == bp.total_brl
        assert rebuilt.members == bp.members
        assert rebuilt.reference_date == bp.reference_date
