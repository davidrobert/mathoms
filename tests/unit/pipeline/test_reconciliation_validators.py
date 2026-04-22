"""Tests — ``SaldoContinuityValidator`` e ``TemporalGapDetector``
(Fase 6 foundation estendida).
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models import BankStatement, Money, Transaction  # noqa: E402
from pipeline.domain.services.reconciliation_validators import (  # noqa: E402
    SaldoContinuityConfig,
    SaldoContinuityValidator,
    SaldoGapWarning,
    TemporalGapConfig,
    TemporalGapDetector,
    TemporalGapWarning,
)


def _stmt(
    period_start: date,
    period_end: date,
    opening: str | None = None,
    closing: str | None = None,
    *,
    institution: str = "itau",
    member: str | None = "david",
    currency: str = "BRL",
    source: str | None = None,
) -> BankStatement:
    return BankStatement(
        institution=institution,
        member_key=member,
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        transactions=[],
        opening_balance=Money.of(opening, currency) if opening is not None else None,
        closing_balance=Money.of(closing, currency) if closing is not None else None,
        source_document=source,
    )


# =============================================================================
# SaldoContinuityConfig
# =============================================================================


class TestSaldoContinuityConfig:
    def test_default_tolerance(self):
        cfg = SaldoContinuityConfig()
        assert cfg.tolerance_amount == Decimal("0.01")

    def test_from_pipeline_config_defaults(self):
        cfg = SaldoContinuityConfig.from_pipeline_config({})
        assert cfg.tolerance_amount == Decimal("0.01")

    def test_from_pipeline_config_custom(self):
        cfg = SaldoContinuityConfig.from_pipeline_config(
            {"reconciliation": {"tolerances": {"saldo_diff": "0.5"}}}
        )
        assert cfg.tolerance_amount == Decimal("0.5")

    def test_from_pipeline_config_none_safe(self):
        cfg = SaldoContinuityConfig.from_pipeline_config(None)  # type: ignore[arg-type]
        assert cfg.tolerance_amount == Decimal("0.01")


# =============================================================================
# SaldoContinuityValidator
# =============================================================================


class TestSaldoContinuityValidator:
    def _svc(self, tolerance: str = "0.01") -> SaldoContinuityValidator:
        return SaldoContinuityValidator(SaldoContinuityConfig(tolerance_amount=Decimal(tolerance)))

    def test_no_statements_no_warnings(self):
        assert self._svc().validate([]) == []

    def test_single_statement_no_warnings(self):
        stmts = [_stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000")]
        assert self._svc().validate(stmts) == []

    def test_continuous_saldos_no_warnings(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000"),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), "1000", "2000"),
        ]
        assert self._svc().validate(stmts) == []

    def test_gap_within_tolerance_no_warning(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000.00"),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), "1000.005", "2000"),
        ]
        # diff = 0.005 ≤ 0.01 → no warning
        assert self._svc().validate(stmts) == []

    def test_gap_above_tolerance_produces_warning(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000", source="a.pdf"),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), "999", "2000", source="b.pdf"),
        ]
        warns = self._svc().validate(stmts)
        assert len(warns) == 1
        assert warns[0].gap == Money.brl("1.00")
        assert warns[0].previous_source == "a.pdf"
        assert warns[0].next_source == "b.pdf"

    def test_missing_closing_skips_pair(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", None),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), "9999", "0"),
        ]
        assert self._svc().validate(stmts) == []

    def test_missing_opening_skips_pair(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000"),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), None, "2000"),
        ]
        assert self._svc().validate(stmts) == []

    def test_different_accounts_do_not_compare(self):
        """Extratos de bancos diferentes não geram warning mesmo com saldos desiguais."""
        stmts = [
            _stmt(
                date(2026, 1, 1),
                date(2026, 1, 31),
                "0",
                "1000",
                institution="itau",
            ),
            _stmt(
                date(2026, 2, 1),
                date(2026, 2, 28),
                "5000",
                "6000",
                institution="nubank",
            ),
        ]
        assert self._svc().validate(stmts) == []

    def test_different_members_do_not_compare(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000", member="david"),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), "5000", "6000", member="carol"),
        ]
        assert self._svc().validate(stmts) == []

    def test_input_order_does_not_matter(self):
        stmts_ordered = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000"),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), "999", "2000"),
        ]
        stmts_reversed = list(reversed(stmts_ordered))
        assert (
            len(self._svc().validate(stmts_ordered))
            == len(self._svc().validate(stmts_reversed))
            == 1
        )

    def test_does_not_mutate_input(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000"),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), "999", "2000"),
        ]
        before = [(s.period_start, s.opening_balance, s.closing_balance) for s in stmts]
        self._svc().validate(stmts)
        after = [(s.period_start, s.opening_balance, s.closing_balance) for s in stmts]
        assert before == after

    def test_custom_tolerance_accepts_larger_gap(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000"),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), "999", "2000"),
        ]
        # diff = 1.00 ≤ 1.50 → no warning
        assert self._svc("1.50").validate(stmts) == []

    def test_warning_format_human_readable(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), "0", "1000", source="a.pdf"),
            _stmt(date(2026, 2, 1), date(2026, 2, 28), "999", "2000", source="b.pdf"),
        ]
        warns = self._svc().validate(stmts)
        msg = warns[0].format()
        assert "1.00" in msg
        assert "a.pdf" in msg
        assert "b.pdf" in msg


# =============================================================================
# TemporalGapConfig
# =============================================================================


class TestTemporalGapConfig:
    def test_default_tolerance_is_4_days(self):
        assert TemporalGapConfig().tolerance_gap_days == 4

    def test_from_pipeline_config_custom(self):
        cfg = TemporalGapConfig.from_pipeline_config(
            {"reconciliation": {"tolerances": {"temporal_gap_days": 7}}}
        )
        assert cfg.tolerance_gap_days == 7

    def test_from_pipeline_config_defaults(self):
        assert TemporalGapConfig.from_pipeline_config({}).tolerance_gap_days == 4


# =============================================================================
# TemporalGapDetector
# =============================================================================


class TestTemporalGapDetector:
    def _svc(self, days: int = 4) -> TemporalGapDetector:
        return TemporalGapDetector(TemporalGapConfig(tolerance_gap_days=days))

    def test_no_statements(self):
        assert self._svc().detect([]) == []

    def test_single_statement_no_gap(self):
        stmts = [_stmt(date(2026, 1, 1), date(2026, 1, 31))]
        assert self._svc().detect(stmts) == []

    def test_contiguous_periods_no_gap(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31)),
            _stmt(date(2026, 2, 1), date(2026, 2, 28)),
        ]
        assert self._svc().detect(stmts) == []

    def test_gap_within_tolerance(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31)),
            _stmt(date(2026, 2, 4), date(2026, 2, 28)),  # 4-day gap
        ]
        assert self._svc(days=4).detect(stmts) == []

    def test_gap_above_tolerance(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), source="jan.pdf"),
            _stmt(date(2026, 2, 10), date(2026, 2, 28), source="feb.pdf"),
        ]
        warns = self._svc(days=4).detect(stmts)
        assert len(warns) == 1
        assert warns[0].days_gap == 10
        assert warns[0].previous_end == "2026-01-31"
        assert warns[0].next_start == "2026-02-10"
        assert warns[0].previous_source == "jan.pdf"
        assert warns[0].next_source == "feb.pdf"

    def test_overlap_does_not_warn(self):
        """Próximo período começando antes do fim anterior → gap negativo → skip."""
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31)),
            _stmt(date(2026, 1, 20), date(2026, 2, 28)),
        ]
        assert self._svc().detect(stmts) == []

    def test_input_order_does_not_matter(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), source="jan.pdf"),
            _stmt(date(2026, 2, 10), date(2026, 2, 28), source="feb.pdf"),
        ]
        warns_a = self._svc().detect(stmts)
        warns_b = self._svc().detect(list(reversed(stmts)))
        assert len(warns_a) == len(warns_b) == 1

    def test_different_accounts_isolated(self):
        stmts = [
            _stmt(
                date(2026, 1, 1),
                date(2026, 1, 31),
                institution="itau",
                source="itau.pdf",
            ),
            _stmt(
                date(2026, 2, 20),
                date(2026, 2, 28),
                institution="nubank",
                source="nubank.pdf",
            ),
        ]
        assert self._svc().detect(stmts) == []

    def test_multiple_gaps_same_account(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 15)),
            _stmt(date(2026, 2, 1), date(2026, 2, 15)),  # 17-day gap
            _stmt(date(2026, 3, 1), date(2026, 3, 15)),  # 14-day gap
        ]
        warns = self._svc(days=4).detect(stmts)
        assert len(warns) == 2

    def test_warning_format_human_readable(self):
        stmts = [
            _stmt(date(2026, 1, 1), date(2026, 1, 31), source="jan.pdf"),
            _stmt(date(2026, 2, 10), date(2026, 2, 28), source="feb.pdf"),
        ]
        warns = self._svc().detect(stmts)
        msg = warns[0].format()
        assert "10 days" in msg
        assert "2026-01-31" in msg
        assert "2026-02-10" in msg


# =============================================================================
# Cross-service invariantes
# =============================================================================


class TestISPCompliance:
    """Nenhum service recebe StageConfig inteiro — apenas seu próprio config."""

    def test_saldo_validator_needs_only_its_config(self):
        svc = SaldoContinuityValidator(SaldoContinuityConfig())
        assert svc is not None

    def test_gap_detector_needs_only_its_config(self):
        svc = TemporalGapDetector(TemporalGapConfig())
        assert svc is not None

    def test_services_accept_none_config_and_use_defaults(self):
        # Robustez: construtor sem argumento usa defaults.
        SaldoContinuityValidator()  # default config
        TemporalGapDetector()


class TestZeroIOContract:
    """Validadores não abrem arquivos nem falam com o DB."""

    def test_no_path_in_public_api(self):
        # Sanity: nenhum argumento aceita Path.
        import inspect

        sig = inspect.signature(SaldoContinuityValidator.validate)
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            # param.annotation é Iterable[BankStatement] — OK.
            assert "Path" not in str(param.annotation)

        sig2 = inspect.signature(TemporalGapDetector.detect)
        for name, param in sig2.parameters.items():
            if name == "self":
                continue
            assert "Path" not in str(param.annotation)


# =============================================================================
# Smoke: chave de agregação
# =============================================================================


class TestAccountKeyGrouping:
    def test_same_institution_different_case(self):
        """Instituição case-insensitive na chave de agregação."""
        stmts = [
            _stmt(
                date(2026, 1, 1),
                date(2026, 1, 31),
                "0",
                "1000",
                institution="Itau",
            ),
            _stmt(
                date(2026, 2, 1),
                date(2026, 2, 28),
                "999",
                "2000",
                institution="ITAU",
            ),
        ]
        warns = SaldoContinuityValidator().validate(stmts)
        # Mesma conta (case normalizado) → detecta a discontinuidade.
        assert len(warns) == 1
