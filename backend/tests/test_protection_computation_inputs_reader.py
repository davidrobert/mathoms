"""Projeção das fontes relacionais no contrato E5 (ADR-387 PR1)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from backend.app.models.fiscal_rule_set import FiscalRuleSet
from backend.app.models.protection import Protection
from backend.app.models.protection_profile import (
    EconomicDependency,
    FamilyMemberProtectionProfile,
    FamilyMemberTaxProfile,
    ProtectionIncomeDeclaration,
)
from backend.app.services.protection_computation_inputs_reader import (
    project_protection_computation_inputs,
)
from pipeline.domain.protection_computation_inputs import ProtectionComputationInputsV1


def _now() -> datetime:
    return datetime(2026, 8, 15, tzinfo=timezone.utc)


def _profile(*, member_id: str = "m-titular") -> FamilyMemberProtectionProfile:
    return FamilyMemberProtectionProfile(
        id="prof-1",
        workspace_id="ws-1",
        family_member_id=member_id,
        life_policy_inventory_complete_as_of=date(2026, 8, 1),
        created_at=_now(),
        updated_at=_now(),
    )


def _income(*, member_id: str = "m-titular") -> ProtectionIncomeDeclaration:
    return ProtectionIncomeDeclaration(
        id="inc-1",
        workspace_id="ws-1",
        family_member_id=member_id,
        active_net_annual_brl_cents=300_000_00,
        passive_net_annual_brl_cents=12_000_00,
        period_start=date(2025, 8, 1),
        period_end=date(2026, 7, 31),
        observed_months=12,
        basis="cash_receipts_after_source_withholding",
        as_of_date=date(2026, 8, 1),
        source_kind="user_declared",
        created_at=_now(),
        updated_at=_now(),
    )


def _dependency() -> EconomicDependency:
    return EconomicDependency(
        id="dep-1",
        workspace_id="ws-1",
        dependent_family_member_id="m-filho",
        provider_family_member_id="m-titular",
        status="yes",
        durable=True,
        as_of_date=date(2026, 8, 1),
        source_kind="user_declared",
        created_at=_now(),
        updated_at=_now(),
    )


def _policy() -> Protection:
    return Protection(
        id="pol-1",
        workspace_id="ws-1",
        category="invalidez",
        insured_family_member_id="m-titular",
        coverage_brl_cents=0,
        benefit_mode="monthly_income",
        benefit_monthly_brl_cents=8_000_00,
        starts_at=date(2026, 1, 1),
        status="Ativa",
        created_at=_now(),
        updated_at=_now(),
    )


def _tax() -> FamilyMemberTaxProfile:
    return FamilyMemberTaxProfile(
        id="tax-1",
        workspace_id="ws-1",
        family_member_id="m-titular",
        br_succession_uf="RJ",
        us_person_status="not_us_person",
        as_of_date=date(2026, 8, 1),
        source_kind="user_declared",
        created_at=_now(),
        updated_at=_now(),
    )


def _rule(*, rule_id: str = "rule-1", from_date: date = date(2026, 1, 1)) -> FiscalRuleSet:
    return FiscalRuleSet(
        id=rule_id,
        rule_code="US_FBAR",
        jurisdiction_code="US",
        rule_version="2026.1",
        effective_from=from_date,
        parameters_json={"kind": "us_fbar", "aggregate_threshold_usd_cents": 1_000_000},
        source="FinCEN FBAR",
        created_at=_now(),
    )


def _project(**overrides) -> ProtectionComputationInputsV1:
    base = dict(
        captured_at=_now(),
        as_of_date=date(2026, 8, 15),
        pipeline_run_id="run-1",
        profiles=(_profile(),),
        dependencies=(_dependency(),),
        incomes=(_income(),),
        policies=(_policy(),),
        debts=(),
        tax_profiles=(_tax(),),
        fiscal_rules=(_rule(),),
    )
    base.update(overrides)
    return project_protection_computation_inputs(**base)


def test_projection_is_available_and_person_scoped() -> None:
    block = _project()
    assert block.status == "available"
    assert block.incomes[0].active_net_annual_brl_cents == 300_000_00
    assert block.policies[0].benefit_mode == "monthly_income"
    assert block.policies[0].lump_sum_brl_cents == 0
    assert block.tax_profiles[0].br_succession_uf == "RJ"
    assert block.economic_dependencies[0].status == "yes"


def test_ambiguous_fiscal_rule_is_dropped() -> None:
    block = _project(
        fiscal_rules=(
            _rule(rule_id="a", from_date=date(2025, 1, 1)),
            _rule(rule_id="b", from_date=date(2026, 1, 1)),
        )
    )
    assert block.fiscal_rules == ()


def test_invalid_fiscal_payload_is_dropped() -> None:
    bad = _rule()
    bad.parameters_json = {"kind": "us_fbar"}
    block = _project(fiscal_rules=(bad,))
    assert block.fiscal_rules == ()


def test_digest_changes_when_income_changes() -> None:
    first = _project()
    other_income = _income()
    other_income.active_net_annual_brl_cents = 301_000_00
    second = _project(incomes=(other_income,))
    assert first.inputs_digest_sha256 != second.inputs_digest_sha256
