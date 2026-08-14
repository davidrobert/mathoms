"""Regressões A40.l61: ausência de insumo não vira zero no bundle de proteção."""

from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal

from backend.app.models.family_member import FamilyMember
from backend.app.services.protection_bundle_adapter import _bundle_to_response
from backend.app.services.protection_bundle_inputs import ProtectionComputationInputs
from backend.app.services.protection_bundle_populator import populate_protection_bundle
from pipeline.domain.services.protection import USPersonThresholds


def _member(*, key: str, role: str, birth_date: date | None) -> FamilyMember:
    return FamilyMember(
        workspace_id="workspace-sintetico",
        key=key,
        full_name=f"Pessoa {key}",
        short_name=key,
        role=role,
        birth_date=birth_date,
    )


def _bundle(
    members: list[FamilyMember],
    inputs: ProtectionComputationInputs | None = None,
):
    return populate_protection_bundle(
        items=[],
        members=members,
        workspace=None,
        today=date(2026, 8, 13),
        adapter_version=3,
        computation_inputs=inputs,
    )


def _us_thresholds() -> USPersonThresholds:
    return USPersonThresholds(
        fbar_threshold_usd=10_000,
        fatca_single_threshold_usd=50_000,
        fatca_joint_threshold_usd=100_000,
        estate_tax_nra_threshold_usd=60_000,
    )


def test_default_inputs_fail_closed_instead_of_computing_zero() -> None:
    bundle = _bundle([])

    assert bundle["gap_analysis"] == {}
    assert bundle["has_us_exposure"] is None
    assert {item["status"] for item in bundle["calculation_status"].values()} == {"missing_data"}


def test_http_response_preserves_unknown_instead_of_defaulting_false() -> None:
    response = _bundle_to_response(_bundle([]))

    assert response.has_us_exposure is None
    assert response.calculation_status["compliance_us"].status == "missing_data"


def test_filho_minor_enters_life_horizon_with_observed_income_and_debt() -> None:
    members = [
        _member(key="titular", role="titular", birth_date=date(1986, 1, 1)),
        _member(key="filho", role="filho", birth_date=date(2016, 1, 1)),
    ]
    inputs = ProtectionComputationInputs(
        annual_active_income_brl_cents=300_000_00,
        outstanding_debts_brl_cents=100_000_00,
    )

    bundle = _bundle(members, inputs)

    assert bundle["calculation_status"]["vida"]["status"] == "computed"
    assert bundle["gap_analysis"]["vida"]["ideal_brl_cents"] > 0
    assert bundle["gap_analysis"]["vida"]["gap_brl_cents"] > 0


def test_unknown_dependent_birth_date_retains_life_calculation() -> None:
    members = [
        _member(key="titular", role="titular", birth_date=date(1986, 1, 1)),
        _member(key="filho", role="filho", birth_date=None),
    ]
    inputs = ProtectionComputationInputs(
        annual_active_income_brl_cents=300_000_00,
        outstanding_debts_brl_cents=100_000_00,
    )

    bundle = _bundle(members, inputs)

    assert bundle["calculation_status"]["vida"]["status"] == "missing_data"
    assert "dependents_ages" in bundle["calculation_status"]["vida"]["missing_inputs"]
    assert "vida" not in bundle["gap_analysis"]


def test_no_economic_dependent_does_not_publish_ten_times_income() -> None:
    members = [_member(key="titular", role="titular", birth_date=date(1986, 1, 1))]
    inputs = ProtectionComputationInputs(
        annual_active_income_brl_cents=300_000_00,
        outstanding_debts_brl_cents=100_000_00,
    )

    bundle = _bundle(members, inputs)

    assert bundle["calculation_status"]["vida"]["status"] == "not_applicable"
    assert "vida" not in bundle["gap_analysis"]


def test_disability_requires_both_net_income_inputs() -> None:
    incomplete = _bundle(
        [], ProtectionComputationInputs(active_net_monthly_income_brl_cents=20_000_00)
    )
    complete = _bundle(
        [],
        ProtectionComputationInputs(
            active_net_monthly_income_brl_cents=20_000_00,
            passive_net_monthly_income_brl_cents=2_000_00,
        ),
    )

    assert incomplete["calculation_status"]["invalidez"]["status"] == "missing_data"
    assert "invalidez" not in incomplete["gap_analysis"]
    assert complete["calculation_status"]["invalidez"]["status"] == "computed"
    assert complete["gap_analysis"]["invalidez"]["gap_brl_cents"] > 0


def test_itcmd_requires_estate_uf_and_effective_rate() -> None:
    incomplete = _bundle([], ProtectionComputationInputs(gross_estate_brl_cents=5_000_000_00))
    complete = _bundle(
        [],
        ProtectionComputationInputs(
            gross_estate_brl_cents=5_000_000_00,
            itcmd_uf="SP",
            itcmd_aliquota_pct_por_uf={"SP": Decimal("4")},
        ),
    )

    assert incomplete["calculation_status"]["sucessorio"]["status"] == "missing_data"
    assert complete["calculation_status"]["sucessorio"]["status"] == "computed"
    assert complete["gap_analysis"]["sucessorio"]["ideal_brl_cents"] == 200_000_00


def test_us_unknown_is_not_serialized_as_false() -> None:
    explicit_none = ProtectionComputationInputs(
        has_us_assets=False,
        has_us_income=False,
        us_tax_status="none",
        us_assets_usd=0,
        us_thresholds=_us_thresholds(),
    )

    unknown = _bundle([])
    absent = _bundle([], explicit_none)

    assert unknown["has_us_exposure"] is None
    assert unknown["calculation_status"]["compliance_us"]["status"] == "missing_data"
    assert absent["has_us_exposure"] is False
    assert absent["calculation_status"]["compliance_us"]["status"] == "not_applicable"


def test_us_income_evidence_is_visible_but_does_not_run_incomplete_rule() -> None:
    exposed = _bundle(
        [],
        ProtectionComputationInputs(
            has_us_assets=False,
            has_us_income=True,
            us_tax_status="none",
            us_assets_usd=0,
            us_thresholds=_us_thresholds(),
        ),
    )

    assert exposed["has_us_exposure"] is True
    assert exposed["calculation_status"]["compliance_us"]["status"] == "missing_data"
    assert exposed["recommendations"] == []
    assert exposed["auto_inferred_risks"] == []


def test_populator_has_no_todo_zero_or_false_calculator_input() -> None:
    from backend.app.services import protection_bundle_populator

    source = inspect.getsource(protection_bundle_populator)
    forbidden = (
        "annual_active_income_brl_cents=0",
        "outstanding_debts_brl_cents=0",
        "active_net_monthly_income_brl_cents=0",
        "passive_net_monthly_income_brl_cents=0",
        "gross_estate_brl_cents=0",
        "has_us_assets=False",
        "has_us_income=False",
    )
    assert not [needle for needle in forbidden if needle in source]
