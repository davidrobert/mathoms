"""Projeta fontes relacionais no contrato E5 de proteção (ADR-387 PR1)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.debt import Debt
from backend.app.models.fiscal_rule_set import FiscalRuleSet
from backend.app.models.protection import Protection
from backend.app.models.protection_profile import (
    EconomicDependency,
    FamilyMemberProtectionProfile,
    FamilyMemberTaxProfile,
    ProtectionIncomeDeclaration,
)
from pipeline.domain.protection_computation_inputs import (
    DBSourceRef,
    EconomicDependencyInput,
    FamilyMemberTaxInput,
    FiscalRuleInput,
    FiscalRuleSourceRef,
    MemberProtectionProfileInput,
    ProtectionComputationInputsV1,
    ProtectionDebtInput,
    ProtectionIncomeInput,
    ProtectionPolicyInput,
    finalize_inputs,
    parse_fiscal_rule_parameters,
)

_RULE_KIND = {
    "BR_ITCMD": "br_itcmd",
    "US_FBAR": "us_fbar",
    "US_FATCA": "us_fatca",
    "US_ESTATE_NRA": "us_estate_nra",
}


def _row_ref(table: str, record_id: str, observed: datetime) -> DBSourceRef:
    return DBSourceRef(table=table, record_id=record_id, observed_updated_at=observed)


def _map_profile(row: FamilyMemberProtectionProfile) -> MemberProtectionProfileInput:
    return MemberProtectionProfileInput(
        subject_family_member_id=row.family_member_id,
        economic_dependents_complete_as_of=row.economic_dependents_complete_as_of,
        debt_inventory_complete_as_of=row.debt_inventory_complete_as_of,
        life_policy_inventory_complete_as_of=row.life_policy_inventory_complete_as_of,
        disability_policy_inventory_complete_as_of=row.disability_policy_inventory_complete_as_of,
        estate_inventory_complete_as_of=row.estate_inventory_complete_as_of,
        source_ref=_row_ref(row.__tablename__, row.id, row.updated_at),
    )


def _map_dependency(row: EconomicDependency) -> EconomicDependencyInput:
    share = None if row.support_share_pct is None else format(row.support_share_pct, "f")
    return EconomicDependencyInput(
        dependent_family_member_id=row.dependent_family_member_id,
        provider_family_member_id=row.provider_family_member_id,
        status=row.status,  # type: ignore[arg-type]
        support_monthly_brl_cents=row.support_monthly_brl_cents,
        support_share_pct=share,
        dependency_end_date=row.dependency_end_date,
        durable=row.durable,
        as_of_date=row.as_of_date,
        source_ref=_row_ref(row.__tablename__, row.id, row.updated_at),
    )


def _map_income(row: ProtectionIncomeDeclaration) -> ProtectionIncomeInput:
    return ProtectionIncomeInput(
        subject_family_member_id=row.family_member_id,
        active_net_annual_brl_cents=row.active_net_annual_brl_cents,
        passive_net_annual_brl_cents=row.passive_net_annual_brl_cents,
        period_start=row.period_start,
        period_end=row.period_end,
        observed_months=row.observed_months,
        basis=row.basis,  # type: ignore[arg-type]
        as_of_date=row.as_of_date,
        source_ref=_row_ref(row.__tablename__, row.id, row.updated_at),
    )


def _map_policy(row: Protection) -> ProtectionPolicyInput:
    mode = row.benefit_mode if row.benefit_mode in {"lump_sum", "monthly_income"} else None
    return ProtectionPolicyInput(
        policy_id=row.id,
        insured_family_member_id=row.insured_family_member_id,
        category=row.category,
        benefit_mode=mode,  # type: ignore[arg-type]
        lump_sum_brl_cents=int(row.coverage_brl_cents),
        benefit_monthly_brl_cents=row.benefit_monthly_brl_cents,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        source_ref=_row_ref(row.__tablename__, row.id, row.updated_at),
    )


def _map_debt(row: Debt) -> ProtectionDebtInput:
    return ProtectionDebtInput(
        debt_id=row.id,
        subject_family_member_id=row.family_member_id,
        balance_brl_cents=int(row.saldo_devedor_cents),
        needs_review=bool(row.needs_review),
        source_ref=_row_ref(row.__tablename__, row.id, row.updated_at),
    )


def _map_tax(row: FamilyMemberTaxProfile) -> FamilyMemberTaxInput:
    return FamilyMemberTaxInput(
        subject_family_member_id=row.family_member_id,
        br_succession_uf=row.br_succession_uf,
        us_person_status=row.us_person_status,  # type: ignore[arg-type]
        us_filing_status=row.us_filing_status,  # type: ignore[arg-type]
        us_filing_residence=row.us_filing_residence,  # type: ignore[arg-type]
        foreign_financial_accounts_max_usd_cents=row.foreign_financial_accounts_max_usd_cents,
        specified_foreign_assets_end_usd_cents=row.specified_foreign_assets_end_usd_cents,
        specified_foreign_assets_max_usd_cents=row.specified_foreign_assets_max_usd_cents,
        us_situs_estate_assets_usd_cents=row.us_situs_estate_assets_usd_cents,
        estate_tax_treaty_code=row.estate_tax_treaty_code,
        as_of_date=row.as_of_date,
        source_ref=_row_ref(row.__tablename__, row.id, row.updated_at),
    )


def _effective_rules(rows: Iterable[FiscalRuleSet], as_of: date) -> list[FiscalRuleSet]:
    grouped: dict[tuple[str, str], list[FiscalRuleSet]] = defaultdict(list)
    for row in rows:
        if row.effective_from > as_of:
            continue
        if row.effective_to is not None and row.effective_to < as_of:
            continue
        grouped[(row.rule_code, row.jurisdiction_code)].append(row)
    return [matches[0] for matches in grouped.values() if len(matches) == 1]


def _rule_source(row: FiscalRuleSet) -> FiscalRuleSourceRef:
    return FiscalRuleSourceRef(
        record_id=row.id,
        rule_version=row.rule_version,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
    )


def _map_rule(row: FiscalRuleSet) -> FiscalRuleInput | None:
    kind = _RULE_KIND.get(row.rule_code)
    if kind is None:
        return None
    payload = dict(row.parameters_json)
    payload.setdefault("kind", kind)
    try:
        parameters = parse_fiscal_rule_parameters(payload)
    except (ValueError, TypeError):
        return None
    return FiscalRuleInput(
        rule_code=row.rule_code,  # type: ignore[arg-type]
        jurisdiction_code=row.jurisdiction_code,
        parameters=parameters,
        source_ref=_rule_source(row),
    )


def _collections_kwargs(**rows: Iterable) -> dict:
    return {
        "member_profiles": tuple(_map_profile(row) for row in rows["profiles"]),
        "economic_dependencies": tuple(_map_dependency(row) for row in rows["dependencies"]),
        "incomes": tuple(_map_income(row) for row in rows["incomes"]),
        "policies": tuple(_map_policy(row) for row in rows["policies"]),
        "debts": tuple(_map_debt(row) for row in rows["debts"]),
        "tax_profiles": tuple(_map_tax(row) for row in rows["tax_profiles"]),
        "fiscal_rules": tuple(_map_effective_rules(rows["fiscal_rules"], rows["as_of_date"])),
    }


def project_protection_computation_inputs(
    *,
    captured_at: datetime,
    as_of_date: date,
    pipeline_run_id: str | None,
    **rows: object,
) -> ProtectionComputationInputsV1:
    """Monta o contrato available a partir de rows já observadas."""
    return finalize_inputs(
        status="available",
        captured_at=captured_at,
        as_of_date=as_of_date,
        pipeline_run_id=pipeline_run_id,
        **_collections_kwargs(as_of_date=as_of_date, **rows),
    )


def _workspace_rows(db: Session, model, workspace_id: str):
    return db.scalars(select(model).where(model.workspace_id == workspace_id)).all()


def _map_effective_rules(
    fiscal_rules: Iterable[FiscalRuleSet], as_of_date: date
) -> list[FiscalRuleInput]:
    mapped: list[FiscalRuleInput] = []
    for row in _effective_rules(fiscal_rules, as_of_date):
        item = _map_rule(row)
        if item is not None:
            mapped.append(item)
    return mapped


def _load_workspace_sources(db: Session, workspace_id: str) -> dict:
    return {
        "profiles": _workspace_rows(db, FamilyMemberProtectionProfile, workspace_id),
        "dependencies": _workspace_rows(db, EconomicDependency, workspace_id),
        "incomes": _workspace_rows(db, ProtectionIncomeDeclaration, workspace_id),
        "policies": _workspace_rows(db, Protection, workspace_id),
        "debts": _workspace_rows(db, Debt, workspace_id),
        "tax_profiles": _workspace_rows(db, FamilyMemberTaxProfile, workspace_id),
        "fiscal_rules": db.scalars(select(FiscalRuleSet)).all(),
    }


def read_protection_computation_inputs(
    db: Session,
    workspace_id: str,
    *,
    captured_at: datetime,
    as_of_date: date,
    pipeline_run_id: str | None = None,
) -> ProtectionComputationInputsV1:
    """Lê o workspace e sela o digest. Falha de leitura fica no caller."""
    return project_protection_computation_inputs(
        captured_at=captured_at,
        as_of_date=as_of_date,
        pipeline_run_id=pipeline_run_id,
        **_load_workspace_sources(db, workspace_id),
    )


__all__ = [
    "project_protection_computation_inputs",
    "read_protection_computation_inputs",
]
