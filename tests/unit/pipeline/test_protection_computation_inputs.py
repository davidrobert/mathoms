"""Contrato ADR-387: digest canônico e ausência explícita."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from pipeline.domain.protection_computation_inputs import (
    BRITCMDParameters,
    FiscalRuleInput,
    FiscalRuleSourceRef,
    ITCMDBracket,
    finalize_inputs,
    parse_fiscal_rule_parameters,
    unavailable_inputs,
)


def _clock() -> datetime:
    return datetime(2026, 8, 15, tzinfo=timezone.utc)


def test_finalize_inputs_digest_is_stable_and_excludes_itself() -> None:
    first = finalize_inputs(
        status="available",
        captured_at=_clock(),
        as_of_date=date(2026, 8, 15),
        pipeline_run_id="run-1",
    )
    second = finalize_inputs(
        status="available",
        captured_at=_clock(),
        as_of_date=date(2026, 8, 15),
        pipeline_run_id="run-1",
    )

    assert first.inputs_digest_sha256 == second.inputs_digest_sha256
    assert first.inputs_digest_sha256 != "0" * 64
    assert first.status == "available"
    assert first.reason_code is None


def _fbar_rule() -> FiscalRuleInput:
    return FiscalRuleInput(
        rule_code="US_FBAR",
        jurisdiction_code="US",
        parameters=parse_fiscal_rule_parameters(
            {"kind": "us_fbar", "aggregate_threshold_usd_cents": 1_000_000}
        ),
        source_ref=FiscalRuleSourceRef(
            record_id="rule-1", rule_version="2026.1", effective_from=date(2026, 1, 1)
        ),
    )


def test_digest_changes_when_collection_changes() -> None:
    empty = finalize_inputs(status="available", captured_at=_clock(), as_of_date=date(2026, 8, 15))
    with_rule = finalize_inputs(
        status="available",
        captured_at=_clock(),
        as_of_date=date(2026, 8, 15),
        fiscal_rules=(_fbar_rule(),),
    )
    assert empty.inputs_digest_sha256 != with_rule.inputs_digest_sha256


def test_unavailable_requires_reason_and_available_forbids_it() -> None:
    missing = unavailable_inputs(data_analise="2026-04-19")
    assert missing.status == "unavailable"
    assert missing.reason_code == "source_not_injected"
    assert missing.as_of_date == date(2026, 4, 19)

    with pytest.raises(ValidationError):
        finalize_inputs(
            status="unavailable",
            captured_at=_clock(),
            as_of_date=date(2026, 8, 15),
        )
    with pytest.raises(ValidationError):
        finalize_inputs(
            status="available",
            reason_code="source_not_injected",
            captured_at=_clock(),
            as_of_date=date(2026, 8, 15),
        )


def test_itcmd_parameters_are_scenario_not_tax_due() -> None:
    params = parse_fiscal_rule_parameters(
        {
            "kind": "br_itcmd",
            "calculation_mode": "scenario_bracketed",
            "brackets": [{"up_to_brl_cents": None, "rate_basis_points": 400}],
        }
    )
    assert isinstance(params, BRITCMDParameters)
    assert params.calculation_mode == "scenario_bracketed"
    assert params.brackets == (ITCMDBracket(up_to_brl_cents=None, rate_basis_points=400),)


def test_unknown_fiscal_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="us_estate_nra"):
        parse_fiscal_rule_parameters({"kind": "irpf"})
