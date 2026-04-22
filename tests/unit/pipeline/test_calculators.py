"""Tests — calculadoras financeiras (Fase 8 foundation)."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models import (  # noqa: E402
    BankStatement,
    BaselinePatrimonial,
    Money,
    Transaction,
)
from pipeline.domain.services import (  # noqa: E402
    CashFlowAggregator,
    EmergencyReserveCalculator,
    EmergencyReserveConfig,
    FinancialScoreCalculator,
    PatrimonioCalculator,
    ScoreConfig,
)


def _stmt(*transactions, closing_balance: str | None = None) -> BankStatement:
    return BankStatement(
        institution="itau",
        member_key="david",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        currency="BRL",
        transactions=list(transactions),
        closing_balance=Money.brl(closing_balance) if closing_balance else None,
    )


def _tx(y: int, m: int, d: int, desc: str, amount: str) -> Transaction:
    return Transaction(date(y, m, d), desc, Money.brl(amount))


class TestCashFlowAggregator:
    def test_empty_input(self):
        r = CashFlowAggregator().aggregate([])
        assert r.months == ()
        assert r.currency == "BRL"

    def test_groups_by_year_month(self):
        stmt = _stmt(
            _tx(2026, 1, 5, "Salario", "5000"),
            _tx(2026, 1, 20, "Mercado", "-300"),
            _tx(2026, 2, 1, "Salario", "5000"),
            _tx(2026, 2, 15, "Restaurante", "-200"),
        )
        r = CashFlowAggregator().aggregate([stmt])
        assert [m.year_month for m in r.months] == ["2026-01", "2026-02"]
        assert r.months[0].income == Money.brl("5000")
        assert r.months[0].expenses == Money.brl("300")
        assert r.months[0].net == Money.brl("4700")

    def test_ignores_transfer(self):
        tx_transfer = Transaction(
            date(2026, 1, 5), "TED INTERNO", Money.brl("-500"), is_transfer=True
        )
        stmt = _stmt(tx_transfer, _tx(2026, 1, 10, "Mercado", "-100"))
        r = CashFlowAggregator().aggregate([stmt])
        # Apenas a despesa não-transferência foi contabilizada
        assert r.months[0].expenses == Money.brl("100")

    def test_raises_on_mixed_currency(self):
        brl = _stmt(_tx(2026, 1, 5, "A", "10"))
        usd = BankStatement(
            "x",
            None,
            date(2026, 1, 1),
            date(2026, 1, 31),
            "USD",
            [Transaction(date(2026, 1, 5), "A", Money.of("10", "USD"))],
        )
        with pytest.raises(ValueError, match="mesma moeda"):
            CashFlowAggregator().aggregate([brl, usd])


class TestPatrimonioCalculator:
    def test_without_baseline_returns_zero(self):
        r = PatrimonioCalculator().calculate([], None)
        assert r.total == Money.brl("0")
        assert r.assets == Money.brl("0")
        assert r.liabilities == Money.brl("0")

    def test_with_baseline_populates_by_member(self):
        baseline = BaselinePatrimonial(
            total_brl=Money.brl("100000"),
            members={"david": Money.brl("60000"), "elena": Money.brl("40000")},
            reference_date=date(2026, 1, 1),
        )
        r = PatrimonioCalculator().calculate([], baseline)
        assert r.total == Money.brl("100000")
        assert r.by_member["david"] == Money.brl("60000")

    def test_report_to_dict(self):
        baseline = BaselinePatrimonial(
            total_brl=Money.brl("1000"),
            members={"david": Money.brl("1000")},
            reference_date=date(2026, 1, 1),
        )
        r = PatrimonioCalculator().calculate([], baseline).to_dict()
        assert r["total"] == 1000.0
        assert r["by_member"] == {"david": 1000.0}


class TestEmergencyReserveCalculator:
    def test_positive_coverage(self):
        stmt = _stmt(
            _tx(2026, 1, 1, "Mercado", "-1000"),
            _tx(2026, 2, 1, "Mercado", "-1000"),
            _tx(2026, 3, 1, "Mercado", "-1000"),
            closing_balance="12000",
        )
        r = EmergencyReserveCalculator().calculate([stmt])
        assert r.monthly_avg_expenses == Money.brl("1000")
        # 12.000 / 1.000 = 12 meses
        assert r.months_of_coverage == Decimal("12")

    def test_empty_statements(self):
        r = EmergencyReserveCalculator().calculate([])
        assert r.monthly_avg_expenses == Money.brl("0")
        assert r.months_of_coverage == Decimal("0")

    def test_configurable_target(self):
        svc = EmergencyReserveCalculator(EmergencyReserveConfig(target_months=3))
        stmt = _stmt(_tx(2026, 1, 1, "A", "-100"), closing_balance="1000")
        r = svc.calculate([stmt])
        assert r.target_months == 3
        assert r.target == Money.brl("300")


class TestFinancialScoreCalculator:
    def _ctx(self, patrimonio: str, balance: str, expenses: str):
        baseline = BaselinePatrimonial(
            total_brl=Money.brl(patrimonio),
            members={"david": Money.brl(patrimonio)},
            reference_date=date(2026, 1, 1),
        )
        stmt = _stmt(
            _tx(2026, 1, 1, "X", expenses),
            closing_balance=balance,
        )
        cash = CashFlowAggregator().aggregate([stmt])
        pat = PatrimonioCalculator().calculate([stmt], baseline)
        reserve = EmergencyReserveCalculator(EmergencyReserveConfig(target_months=6)).calculate(
            [stmt]
        )
        return pat, reserve, cash

    def test_high_score(self):
        pat, reserve, cash = self._ctx(patrimonio="500000", balance="60000", expenses="-5000")
        score = FinancialScoreCalculator().calculate(pat, reserve, cash)
        # Patrimônio > 0 (40) + reserva suficiente (30) + fluxo negativo (0) = 70
        assert 60 <= score <= 70

    def test_low_score_when_no_patrimonio_and_no_reserve(self):
        pat, reserve, cash = self._ctx(patrimonio="0", balance="0", expenses="-100")
        score = FinancialScoreCalculator().calculate(pat, reserve, cash)
        # Patrimônio = 0 (0) + reserva insuficiente (0) + fluxo negativo (0) = 0
        assert score == 0

    def test_score_clamped_to_100(self):
        pat, reserve, cash = self._ctx(patrimonio="1000000", balance="1000000", expenses="-100")
        svc = FinancialScoreCalculator(
            ScoreConfig(weight_patrimonio=50, weight_reserve=50, weight_positive_flow=50)
        )
        score = svc.calculate(pat, reserve, cash)
        assert score <= 100
