"""Unit tests A29.l2 (ADR-308) — warnings de reconciliação E3 projetam ReviewReason.

Cobre: (a) as 4 famílias novas (`domain.*`) projetam com offending_value sem
valor monetário (Money é dado sensível); (b) gate de needs_review continua
restrito a BLOCKING_CODES — domain.* é informativo e não pausa o run.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.transaction import Money
from pipeline.domain.review_reason import BLOCKING_CODES, ReviewReasonCode
from pipeline.domain.services.account_grouper import AccountKey
from pipeline.domain.services.anachronic_guard import AnachronicTransactionWarning
from pipeline.domain.services.baseline_validator import BaselineDiffWarning
from pipeline.domain.services.reconciliation_validators import (
    ContinuityAccountKey,
    SaldoGapWarning,
    TemporalGapWarning,
)

_KW = dict(stage="reconcile_transactions", artifact_key="fallback_key", document_id=None)
# Chave da cadeia de continuidade (ADR-310) — deriva da AccountKey canônica.
_ACCOUNT = ContinuityAccountKey(
    account=AccountKey(bank="itau", account_type="extratoconta", currency="BRL"),
    member="david",
    account_number=None,
)
# Baseline IRPF mantém a chave tupla (instituição, membro, moeda).
_BASELINE_ACCOUNT = ("itau", "david", "BRL")
_MONETARY_RE = re.compile(r"\d+[.,]\d{2}\b")


def _saldo_warning() -> SaldoGapWarning:
    return SaldoGapWarning(
        account_key=_ACCOUNT,
        previous_source="abc123_itau_extratoconta_202601-3.json",
        next_source="def456_itau_extratoconta_202602-3.json",
        previous_closing=Money.of("1868.38", "BRL"),
        next_opening=Money.of("2500.00", "BRL"),
        gap=Money.of("631.62", "BRL"),
    )


def _baseline_warning() -> BaselineDiffWarning:
    return BaselineDiffWarning(
        account_key=_BASELINE_ACCOUNT,
        reference_date=date(2024, 12, 31),
        baseline_saldo=Money.of("10000.00", "BRL"),
        statement_closing=Money.of("8123.45", "BRL"),
        diff=Money.of("1876.55", "BRL"),
        baseline_member="david",
    )


class TestMonetaryRedactionByConstruction:
    def test_saldo_gap_offending_value_has_no_monetary_figure(self) -> None:
        rr = _saldo_warning().to_review_reason(**_KW)
        assert rr is not None
        assert rr.code == ReviewReasonCode.domain_balance_gap
        assert not _MONETARY_RE.search(rr.offending_value), rr.offending_value
        assert not _MONETARY_RE.search(rr.message)

    def test_baseline_divergence_only_carries_percent(self) -> None:
        rr = _baseline_warning().to_review_reason(**_KW)
        assert rr is not None
        assert rr.code == ReviewReasonCode.domain_baseline_divergence
        # Percentual relativo é permitido; valor absoluto de saldo/diff não.
        assert "%" in rr.offending_value
        assert "10000" not in rr.offending_value
        assert "1876" not in rr.offending_value


class TestProjectionFields:
    def test_temporal_gap_projects_with_next_source_as_artifact_key(self) -> None:
        w = TemporalGapWarning(
            account_key=_ACCOUNT,
            previous_source="a_202601.json",
            next_source="b_202603.json",
            days_gap=54,
            previous_end="2026-01-31",
            next_start="2026-03-26",
        )
        rr = w.to_review_reason(**_KW)
        assert rr is not None
        assert rr.code == ReviewReasonCode.domain_temporal_gap
        assert rr.artifact_key == "b_202603.json"
        assert "54 dias" in rr.offending_value

    def test_anachronic_projects_with_source_and_count(self) -> None:
        w = AnachronicTransactionWarning(
            source="eed6c1_itau_cdb_2025",
            periodo_inicio="2025-12-01",
            cutoff="2025-06-04",
            dropped_count=2,
        )
        rr = w.to_review_reason(**_KW)
        assert rr is not None
        assert rr.code == ReviewReasonCode.domain_anachronic_transaction
        assert rr.artifact_key == "eed6c1_itau_cdb_2025"
        assert "2" in rr.offending_value

    def test_baseline_artifact_key_fallback_when_empty(self) -> None:
        rr = _baseline_warning().to_review_reason(
            stage="reconcile_transactions", artifact_key="", document_id=None
        )
        assert rr is not None
        assert rr.artifact_key == "itau_BRL_baseline_2024"


class TestBlockingGate:
    def test_domain_codes_are_not_blocking(self) -> None:
        for code in (
            ReviewReasonCode.domain_balance_gap,
            ReviewReasonCode.domain_temporal_gap,
            ReviewReasonCode.domain_anachronic_transaction,
            ReviewReasonCode.domain_baseline_divergence,
        ):
            assert code not in BLOCKING_CODES

    def test_a28l8_codes_remain_blocking(self) -> None:
        assert ReviewReasonCode.extract_missing_required_field in BLOCKING_CODES
        assert ReviewReasonCode.dedup_sentinel_period in BLOCKING_CODES

    def test_validation_block_only_blocks_on_blocking_codes(self) -> None:
        from scripts.reconcile_transactions import _e3_validation_block

        class _Result:
            review_reasons = (
                _saldo_warning().to_review_reason(**_KW),
                _baseline_warning().to_review_reason(**_KW),
            )

        block = _e3_validation_block(_Result())
        assert block["valid"] is True
        assert block["errors"] == []
        assert len(block["review_reasons"]) == 2

    def test_validation_block_blocks_when_blocking_reason_present(self) -> None:
        from pipeline.domain.services.e3_reconciler_adapter import EmptyInstitutionWarning
        from scripts.reconcile_transactions import _e3_validation_block

        class _Result:
            review_reasons = (
                EmptyInstitutionWarning(source="x").to_review_reason(**_KW),
                _saldo_warning().to_review_reason(**_KW),
            )

        block = _e3_validation_block(_Result())
        assert block["valid"] is False
        assert len(block["errors"]) == 1
        assert len(block["review_reasons"]) == 2
