"""Calcula o bundle pinado a partir do V1 — sem consultar estado live."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.protection_bundle_adapter import (
    _PROTECTION_BUNDLE_VERSION,
    _bundle_to_response,
)
from backend.app.services.protection_bundle_inputs import ProtectionComputationInputs
from backend.app.services.protection_bundle_populator import populate_protection_bundle
from pipeline.domain.protection_bundle import DocumentaryCoverage, ProtectionItem
from pipeline.domain.protection_computation_inputs import (
    MemberProtectionProfileInput,
    ProtectionComputationInputsV1,
    ProtectionIncomeInput,
    ProtectionPolicyInput,
)


def compute_protection_bundle(
    inputs: ProtectionComputationInputsV1,
    *,
    as_of_date: date,
    documentary_coverage: DocumentaryCoverage | None = None,
) -> dict:
    """Fotografia computada do run. Capital único não vira renda mensal."""
    bundle = populate_protection_bundle(
        items=_items_from_policies(inputs.policies),
        members=_members_from_profiles(inputs.member_profiles),
        workspace=None,
        today=as_of_date,
        adapter_version=_PROTECTION_BUNDLE_VERSION,
        computation_inputs=_computation_from_v1(inputs),
        documentary_coverage=documentary_coverage,
    )
    return _jsonable(_bundle_to_response(bundle).model_dump())


def _jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _items_from_policies(policies: tuple[ProtectionPolicyInput, ...]) -> list[ProtectionItem]:
    return [_policy_item(policy) for policy in policies if policy.status == "Ativa"]


def _policy_item(policy: ProtectionPolicyInput) -> ProtectionItem:
    ends = None if policy.ends_at is None else policy.ends_at.isoformat()
    return {
        "id": policy.policy_id,
        "category": policy.category,
        "holder_family_member_id": None,
        "insured_family_member_id": policy.insured_family_member_id,
        "insurer": None,
        "coverage_brl_cents": policy.lump_sum_brl_cents,
        "premium_monthly_brl_cents": None,
        "benefit_mode": policy.benefit_mode,
        "benefit_monthly_brl_cents": policy.benefit_monthly_brl_cents,
        "coverage_type": None,
        "starts_at": policy.starts_at.isoformat(),
        "ends_at": ends,
        "status": policy.status,
    }


def _members_from_profiles(profiles: tuple[MemberProtectionProfileInput, ...]) -> list:
    return [
        SimpleNamespace(
            id=profile.subject_family_member_id,
            role=profile.role or "other",
            birth_date=profile.birth_date,
        )
        for profile in profiles
    ]


def _computation_from_v1(inputs: ProtectionComputationInputsV1) -> ProtectionComputationInputs:
    subject = _primary_subject(inputs)
    income = _income_for(inputs, subject)
    monthly_active, monthly_passive = _monthly_pair(income)
    annual = None if income is None else income.active_net_annual_brl_cents
    return ProtectionComputationInputs(
        annual_active_income_brl_cents=annual,
        outstanding_debts_brl_cents=_debts_for(inputs, subject),
        active_net_monthly_income_brl_cents=monthly_active,
        passive_net_monthly_income_brl_cents=monthly_passive,
    )


def _primary_subject(inputs: ProtectionComputationInputsV1) -> str | None:
    titulares = [
        profile.subject_family_member_id
        for profile in inputs.member_profiles
        if profile.role == "titular"
    ]
    if len(titulares) == 1:
        return titulares[0]
    subjects = {income.subject_family_member_id for income in inputs.incomes}
    return next(iter(subjects)) if len(subjects) == 1 else None


def _income_for(
    inputs: ProtectionComputationInputsV1, subject: str | None
) -> ProtectionIncomeInput | None:
    if subject is None:
        return None
    matches = [row for row in inputs.incomes if row.subject_family_member_id == subject]
    return matches[0] if len(matches) == 1 else None


def _monthly_pair(income: ProtectionIncomeInput | None) -> tuple[int | None, int | None]:
    if income is None or income.observed_months != 12:
        return None, None
    active = income.active_net_annual_brl_cents
    passive = income.passive_net_annual_brl_cents
    return (
        None if active is None else active // 12,
        None if passive is None else passive // 12,
    )


def _debts_for(inputs: ProtectionComputationInputsV1, subject: str | None) -> int | None:
    if subject is None:
        return None
    usable = [
        debt
        for debt in inputs.debts
        if not debt.needs_review and debt.subject_family_member_id in {subject, None}
    ]
    if usable:
        return sum(debt.balance_brl_cents for debt in usable)
    return _confirmed_zero_debt(inputs, subject)


def _confirmed_zero_debt(inputs: ProtectionComputationInputsV1, subject: str) -> int | None:
    profile = next(
        (row for row in inputs.member_profiles if row.subject_family_member_id == subject),
        None,
    )
    if profile is not None and profile.debt_inventory_complete_as_of is not None:
        return 0
    return None


__all__ = ["compute_protection_bundle"]
