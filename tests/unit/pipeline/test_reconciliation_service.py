"""Tests — ``ReconciliationService`` (Fase 6)."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.models import BankStatement, Money, Transaction  # noqa: E402
from pipeline.domain.services import ReconciliationConfig, ReconciliationService  # noqa: E402


def _tx(day: int, desc: str, amount: str) -> Transaction:
    return Transaction(
        date=date(2026, 1, day),
        description=desc,
        amount=Money.brl(amount),
    )


class TestConfig:
    def test_from_pipeline_config_defaults(self):
        cfg = ReconciliationConfig.from_pipeline_config({})
        assert cfg.tolerance_days == 3
        assert cfg.tolerance_amount == Decimal("0.01")
        assert cfg.skip_types == frozenset()

    def test_from_pipeline_config_custom(self):
        cfg = ReconciliationConfig.from_pipeline_config(
            {"reconciliation": {"tolerance_days": 5, "tolerance_amount": "0.05"}}
        )
        assert cfg.tolerance_days == 5
        assert cfg.tolerance_amount == Decimal("0.05")


class TestIsDuplicate:
    def _svc(self, **kwargs):
        return ReconciliationService(ReconciliationConfig(**kwargs))

    def test_exact_duplicate(self):
        a = _tx(5, "MERCADO", "-100")
        b = _tx(5, "MERCADO", "-100")
        assert self._svc().is_duplicate(a, b)

    def test_fuzzy_within_tolerance_days(self):
        a = _tx(5, "MERCADO", "-100")
        b = _tx(7, "MERCADO", "-100")
        assert self._svc(tolerance_days=3).is_duplicate(a, b)

    def test_outside_tolerance_days(self):
        a = _tx(5, "MERCADO", "-100")
        b = _tx(15, "MERCADO", "-100")
        assert not self._svc(tolerance_days=3).is_duplicate(a, b)

    def test_different_description_not_duplicate(self):
        a = _tx(5, "MERCADO", "-100")
        b = _tx(5, "RESTAURANTE", "-100")
        assert not self._svc().is_duplicate(a, b)

    def test_different_currency_not_duplicate(self):
        a = Transaction(date(2026, 1, 5), "X", Money.brl("100"))
        b = Transaction(date(2026, 1, 5), "X", Money.of("100", "USD"))
        assert not self._svc().is_duplicate(a, b)


class TestIsTransferPair:
    def test_opposing_values_same_day(self):
        svc = ReconciliationService(ReconciliationConfig())
        a = _tx(5, "TED SAIDA", "-500")
        b = _tx(5, "TED ENTRADA", "500")
        assert svc.is_transfer_pair(a, b)

    def test_opposing_within_tolerance(self):
        svc = ReconciliationService(ReconciliationConfig(tolerance_days=3))
        a = _tx(5, "TED SAIDA", "-500")
        b = _tx(7, "TED ENTRADA", "500")
        assert svc.is_transfer_pair(a, b)

    def test_non_opposing_not_transfer(self):
        svc = ReconciliationService(ReconciliationConfig())
        a = _tx(5, "X", "-500")
        b = _tx(5, "Y", "-500")
        assert not svc.is_transfer_pair(a, b)


class TestReconcile:
    def test_removes_duplicates_in_single_statement(self):
        stmt = BankStatement(
            institution="itau",
            member_key="david",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            currency="BRL",
            transactions=[
                _tx(5, "MERCADO", "-100"),
                _tx(5, "MERCADO", "-100"),  # duplicata
                _tx(10, "UBER", "-30"),
            ],
        )
        out = ReconciliationService(ReconciliationConfig()).reconcile([stmt])
        assert len(out) == 1
        assert [t.description for t in out[0].transactions] == ["MERCADO", "UBER"]

    def test_preserves_unique_transactions(self):
        stmt = BankStatement(
            institution="itau",
            member_key="david",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            currency="BRL",
            transactions=[
                _tx(5, "A", "-10"),
                _tx(6, "B", "-20"),
                _tx(7, "C", "-30"),
            ],
        )
        out = ReconciliationService(ReconciliationConfig()).reconcile([stmt])
        assert len(out[0].transactions) == 3

    def test_original_statement_not_mutated(self):
        stmt = BankStatement(
            institution="x",
            member_key=None,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            currency="BRL",
            transactions=[_tx(5, "A", "-10"), _tx(5, "A", "-10")],
        )
        before_count = len(stmt.transactions)
        ReconciliationService(ReconciliationConfig()).reconcile([stmt])
        assert len(stmt.transactions) == before_count

    def test_groups_by_institution(self):
        stmts = [
            BankStatement(
                "itau", None, date(2026, 1, 1), date(2026, 1, 31), "BRL", [_tx(5, "A", "-10")]
            ),
            BankStatement(
                "nubank", None, date(2026, 1, 1), date(2026, 1, 31), "BRL", [_tx(5, "A", "-10")]
            ),
        ]
        out = ReconciliationService(ReconciliationConfig()).reconcile(stmts)
        assert len(out) == 2


class TestZeroIOContract:
    """Service não pode importar ``scripts.pipeline_common`` nem ler disco."""

    def test_in_memory_store_is_sufficient_fixture(self):
        store = InMemoryArtifactStore()
        # Fixture de 3 linhas
        cfg = ReconciliationConfig(tolerance_days=3, tolerance_amount=Decimal("0.01"))
        svc = ReconciliationService(cfg)
        stmt = BankStatement(
            "x", None, date(2026, 1, 1), date(2026, 1, 31), "BRL", [_tx(5, "A", "-10")]
        )
        out = svc.reconcile([stmt])
        assert out[0].transactions == stmt.transactions
