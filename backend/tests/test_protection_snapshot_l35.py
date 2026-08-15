"""A40.l35: snapshot.bundle é calculado do V1, sem live GET."""

from __future__ import annotations

import inspect
from datetime import date, datetime, timezone

from backend.app.services.protection_snapshot_builder import build_protection_snapshot
from backend.app.services.protection_snapshot_compute import compute_protection_bundle
from pipeline.domain.protection_computation_inputs import (
    DBSourceRef,
    MemberProtectionProfileInput,
    ProtectionIncomeInput,
    ProtectionPolicyInput,
    finalize_inputs,
)


def _now() -> datetime:
    return datetime(2026, 8, 15, tzinfo=timezone.utc)


def _ref(record_id: str) -> DBSourceRef:
    return DBSourceRef(table="t", record_id=record_id, observed_updated_at=_now())


def _profile(*, member_id: str, role: str, birth: date, debt_done: bool = False):
    complete = date(2026, 8, 1) if debt_done else None
    return MemberProtectionProfileInput(
        subject_family_member_id=member_id,
        role=role,
        birth_date=birth,
        debt_inventory_complete_as_of=complete,
        source_ref=_ref(member_id),
    )


def _income(*, months: int = 12) -> ProtectionIncomeInput:
    return ProtectionIncomeInput(
        subject_family_member_id="m-titular",
        active_net_annual_brl_cents=300_000_00,
        passive_net_annual_brl_cents=12_000_00,
        period_start=date(2025, 8, 1),
        period_end=date(2026, 7, 31),
        observed_months=months,
        basis="cash_receipts_after_source_withholding",
        as_of_date=date(2026, 8, 1),
        source_ref=_ref("inc-1"),
    )


def _policy(*, mode: str, lump: int = 0, monthly: int | None = None, status: str = "Ativa"):
    return ProtectionPolicyInput(
        policy_id="pol-1",
        insured_family_member_id="m-titular",
        category="invalidez",
        benefit_mode=mode,  # type: ignore[arg-type]
        lump_sum_brl_cents=lump,
        benefit_monthly_brl_cents=monthly,
        starts_at=date(2026, 1, 1),
        status=status,
        source_ref=_ref("pol-1"),
    )


def _default_profiles():
    titular = _profile(
        member_id="m-titular", role="titular", birth=date(1986, 1, 1), debt_done=True
    )
    filho = _profile(member_id="m-filho", role="filho", birth=date(2016, 1, 1))
    return (titular, filho)


def _family_inputs(**overrides):
    base = dict(member_profiles=_default_profiles(), incomes=(_income(),))
    base.update(overrides)
    return finalize_inputs(
        status="available",
        captured_at=_now(),
        as_of_date=date(2026, 8, 15),
        pipeline_run_id="run-1",
        **base,
    )


def _e5(inputs) -> dict:
    return {
        "data_analise": "2026-08-15",
        "protection_computation_inputs_v1": inputs.model_dump(mode="json"),
    }


def _snapshot(inputs) -> dict:
    return build_protection_snapshot(
        e5_payload=_e5(inputs),
        pipeline_run_id="run-1",
        analysis_artifact_id=9,
    )


def test_filho_with_observed_income_computes_life_gap() -> None:
    bundle = _snapshot(_family_inputs())["bundle"]
    assert bundle["calculation_status"]["vida"]["status"] == "computed"
    assert bundle["gap_analysis"]["vida"]["ideal_brl"] > 0
    assert bundle["gap_analysis"]["vida"]["gap_brl"] > 0


def test_lump_sum_disability_does_not_become_monthly_income() -> None:
    inputs = _family_inputs(policies=(_policy(mode="lump_sum", lump=1_200_000_00),))
    status = _snapshot(inputs)["bundle"]["calculation_status"]["invalidez"]
    assert status["status"] == "missing_data"
    assert "disability_monthly_benefit" in status["missing_inputs"]


def test_monthly_disability_computes_when_year_is_complete() -> None:
    inputs = _family_inputs(
        policies=(_policy(mode="monthly_income", monthly=8_000_00),),
    )
    bundle = _snapshot(inputs)["bundle"]
    assert bundle["calculation_status"]["invalidez"]["status"] == "computed"
    assert bundle["gap_analysis"]["invalidez"]["gap_brl"] != 0


def test_partial_year_income_does_not_invent_monthly() -> None:
    inputs = _family_inputs(incomes=(_income(months=11),))
    status = _snapshot(inputs)["bundle"]["calculation_status"]["invalidez"]
    assert status["status"] == "missing_data"


def test_cancelled_policy_is_excluded_from_bundle() -> None:
    cancelled = _policy(mode="monthly_income", monthly=8_000_00, status="Cancelada")
    inputs = _family_inputs(policies=(cancelled,))
    assert _snapshot(inputs)["bundle"]["policies"] == []


def test_itcmd_stays_missing_without_estate_scenario() -> None:
    status = _snapshot(_family_inputs())["bundle"]["calculation_status"]["sucessorio"]
    assert status["status"] == "missing_data"


def test_compute_source_never_divides_lump_sum_by_twelve() -> None:
    module = inspect.getsource(
        __import__(
            "backend.app.services.protection_snapshot_compute",
            fromlist=["compute_protection_bundle"],
        )
    )
    assert "lump_sum" not in module or "lump_sum_brl_cents / 12" not in module
    assert "coverage_brl" not in module or "coverage_brl_cents / 12" not in module


def test_unavailable_inputs_still_have_null_bundle() -> None:
    snap = build_protection_snapshot(
        e5_payload={"data_analise": "2026-08-15"},
        pipeline_run_id="run-1",
        analysis_artifact_id=9,
    )
    assert snap["snapshot_status"] == "unavailable"
    assert snap["bundle"] is None
