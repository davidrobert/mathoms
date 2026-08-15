"""Contrato run-scoped dos insumos de proteção (ADR-387)."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DBSourceRef(_StrictModel):
    kind: Literal["db_row"] = "db_row"
    table: str
    record_id: str
    observed_updated_at: datetime


class FiscalRuleSourceRef(_StrictModel):
    kind: Literal["fiscal_rule_set"] = "fiscal_rule_set"
    record_id: str
    rule_version: str
    effective_from: date
    effective_to: date | None = None


SourceRef = Annotated[Union[DBSourceRef, FiscalRuleSourceRef], Field(discriminator="kind")]


class MemberProtectionProfileInput(_StrictModel):
    subject_family_member_id: str
    economic_dependents_complete_as_of: date | None = None
    debt_inventory_complete_as_of: date | None = None
    life_policy_inventory_complete_as_of: date | None = None
    disability_policy_inventory_complete_as_of: date | None = None
    estate_inventory_complete_as_of: date | None = None
    source_ref: DBSourceRef


class EconomicDependencyInput(_StrictModel):
    dependent_family_member_id: str
    provider_family_member_id: str
    status: Literal["yes", "no", "unknown"]
    support_monthly_brl_cents: int | None = Field(default=None, ge=0)
    support_share_pct: str | None = None
    dependency_end_date: date | None = None
    durable: bool
    as_of_date: date
    source_ref: DBSourceRef


class ProtectionIncomeInput(_StrictModel):
    subject_family_member_id: str
    active_net_annual_brl_cents: int | None = Field(default=None, ge=0)
    passive_net_annual_brl_cents: int | None = Field(default=None, ge=0)
    period_start: date
    period_end: date
    observed_months: int = Field(ge=1, le=12)
    basis: Literal["cash_receipts_after_source_withholding"]
    as_of_date: date
    source_ref: DBSourceRef


class ProtectionPolicyInput(_StrictModel):
    policy_id: str
    insured_family_member_id: str | None = None
    category: str
    benefit_mode: Literal["lump_sum", "monthly_income"] | None = None
    lump_sum_brl_cents: int = Field(ge=0)
    benefit_monthly_brl_cents: int | None = Field(default=None, ge=0)
    starts_at: date
    ends_at: date | None = None
    source_ref: DBSourceRef


class ProtectionDebtInput(_StrictModel):
    debt_id: str
    subject_family_member_id: str | None = None
    balance_brl_cents: int = Field(ge=0)
    needs_review: bool
    source_ref: DBSourceRef


class FamilyMemberTaxInput(_StrictModel):
    subject_family_member_id: str
    br_succession_uf: str | None = Field(default=None, pattern="^[A-Z]{2}$")
    us_person_status: Literal["us_person", "not_us_person", "unknown"] | None = None
    us_filing_status: (
        Literal["single", "married_joint", "married_separate", "other", "unknown"] | None
    ) = None
    us_filing_residence: Literal["inside_us", "outside_us", "unknown"] | None = None
    foreign_financial_accounts_max_usd_cents: int | None = Field(default=None, ge=0)
    specified_foreign_assets_end_usd_cents: int | None = Field(default=None, ge=0)
    specified_foreign_assets_max_usd_cents: int | None = Field(default=None, ge=0)
    us_situs_estate_assets_usd_cents: int | None = Field(default=None, ge=0)
    estate_tax_treaty_code: str | None = None
    as_of_date: date
    source_ref: DBSourceRef


class ITCMDBracket(_StrictModel):
    up_to_brl_cents: int | None = Field(default=None, ge=0)
    rate_basis_points: int = Field(ge=0, le=10_000)


class BRITCMDParameters(_StrictModel):
    kind: Literal["br_itcmd"] = "br_itcmd"
    calculation_mode: Literal["scenario_bracketed"]
    brackets: tuple[ITCMDBracket, ...] = Field(min_length=1)


class USFBARParameters(_StrictModel):
    kind: Literal["us_fbar"] = "us_fbar"
    aggregate_threshold_usd_cents: int = Field(ge=0)


class FATCAThreshold(_StrictModel):
    filing_status: Literal["single", "married_joint", "married_separate", "other"]
    residence: Literal["inside_us", "outside_us"]
    year_end_usd_cents: int = Field(ge=0)
    any_time_usd_cents: int = Field(ge=0)


class USFATCAParameters(_StrictModel):
    kind: Literal["us_fatca"] = "us_fatca"
    thresholds: tuple[FATCAThreshold, ...] = Field(min_length=1)


class USEstateNRAParameters(_StrictModel):
    kind: Literal["us_estate_nra"] = "us_estate_nra"
    filing_threshold_usd_cents: int = Field(ge=0)


FiscalRuleParameters = Annotated[
    Union[BRITCMDParameters, USFBARParameters, USFATCAParameters, USEstateNRAParameters],
    Field(discriminator="kind"),
]


class FiscalRuleInput(_StrictModel):
    rule_code: Literal["BR_ITCMD", "US_FBAR", "US_FATCA", "US_ESTATE_NRA"]
    jurisdiction_code: str
    parameters: FiscalRuleParameters
    source_ref: FiscalRuleSourceRef


class ProtectionComputationInputsV1(_StrictModel):
    input_contract_version: Literal[1] = 1
    status: Literal["available", "unavailable"]
    reason_code: Literal["source_not_injected", "source_read_failed"] | None = None
    pipeline_run_id: str | None = None
    captured_at: datetime
    as_of_date: date
    inputs_digest_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    member_profiles: tuple[MemberProtectionProfileInput, ...] = ()
    economic_dependencies: tuple[EconomicDependencyInput, ...] = ()
    incomes: tuple[ProtectionIncomeInput, ...] = ()
    policies: tuple[ProtectionPolicyInput, ...] = ()
    debts: tuple[ProtectionDebtInput, ...] = ()
    tax_profiles: tuple[FamilyMemberTaxInput, ...] = ()
    fiscal_rules: tuple[FiscalRuleInput, ...] = ()

    @model_validator(mode="after")
    def validate_availability(self) -> "ProtectionComputationInputsV1":
        if self.status == "available" and self.reason_code is not None:
            raise ValueError("available inputs must not carry reason_code")
        if self.status == "unavailable" and self.reason_code is None:
            raise ValueError("unavailable inputs require reason_code")
        return self


def finalize_inputs(
    *,
    status: Literal["available", "unavailable"],
    captured_at: datetime,
    as_of_date: date,
    pipeline_run_id: str | None = None,
    reason_code: Literal["source_not_injected", "source_read_failed"] | None = None,
    **collections: object,
) -> ProtectionComputationInputsV1:
    """Valida o contrato e sela o digest da projeção canônica."""
    draft = ProtectionComputationInputsV1(
        status=status,
        reason_code=reason_code,
        pipeline_run_id=pipeline_run_id,
        captured_at=captured_at,
        as_of_date=as_of_date,
        inputs_digest_sha256="0" * 64,
        **collections,
    )
    return _seal_digest(draft)


def _seal_digest(draft: ProtectionComputationInputsV1) -> ProtectionComputationInputsV1:
    canonical = draft.model_dump(mode="json", exclude={"inputs_digest_sha256"})
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return draft.model_copy(update={"inputs_digest_sha256": hashlib.sha256(encoded).hexdigest()})


def analysis_clock(data_analise: str) -> tuple[datetime, date]:
    """Relógio determinístico do artefato E5 — não consulta date.today()."""
    as_of = date.fromisoformat(data_analise[:10])
    return datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc), as_of


def unavailable_inputs(
    *,
    data_analise: str,
    reason_code: Literal["source_not_injected", "source_read_failed"] = "source_not_injected",
) -> ProtectionComputationInputsV1:
    captured_at, as_of_date = analysis_clock(data_analise)
    return finalize_inputs(
        status="unavailable",
        reason_code=reason_code,
        captured_at=captured_at,
        as_of_date=as_of_date,
    )


def parse_fiscal_rule_parameters(payload: dict[str, object]) -> FiscalRuleParameters:
    """Valida o JSON persistido contra o modelo discriminado da regra."""
    kind = payload.get("kind")
    if kind == "br_itcmd":
        return BRITCMDParameters.model_validate(payload)
    if kind == "us_fbar":
        return USFBARParameters.model_validate(payload)
    if kind == "us_fatca":
        return USFATCAParameters.model_validate(payload)
    if kind == "us_estate_nra":
        return USEstateNRAParameters.model_validate(payload)
    raise ValueError(
        f"expected fiscal rule kind br_itcmd|us_fbar|us_fatca|us_estate_nra, got {kind!r}"
    )


__all__ = [
    "DBSourceRef",
    "EconomicDependencyInput",
    "FamilyMemberTaxInput",
    "FiscalRuleInput",
    "MemberProtectionProfileInput",
    "ProtectionComputationInputsV1",
    "ProtectionDebtInput",
    "ProtectionIncomeInput",
    "ProtectionPolicyInput",
    "analysis_clock",
    "finalize_inputs",
    "parse_fiscal_rule_parameters",
    "unavailable_inputs",
]
