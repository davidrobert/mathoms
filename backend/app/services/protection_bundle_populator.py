"""Populator fail-closed do ``ProtectionBundle`` (ADR-192; A40.l61)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.core.logging import get_logger
from backend.app.models.family_member import FamilyMember
from backend.app.models.workspace import Workspace
from backend.app.services.protection_bundle_inputs import ProtectionComputationInputs
from backend.app.services.protection_calculation_status import (
    calculation_statuses,
    dependent_ages,
    disability_monthly_benefit,
    principal_age,
)
from pipeline.domain.protection_bundle import (
    DocumentaryCoverage,
    ProtectionBundle,
    ProtectionCalculationStatus,
    ProtectionGapItem,
    ProtectionItem,
    ProtectionRecommendation,
    ProtectionThresholds,
    RiskInferred,
)
from pipeline.domain.services.protection import (
    ComplianceFlag,
    DisabilityInputs,
    ITCMDInputs,
    LifeInsuranceInputs,
    USExposureInputs,
    compliance_risk_us_person,
    disability_coverage_gap,
    itcmd_estimated,
    life_insurance_coverage_ideal,
)

logger = get_logger("mathoms.protection.populator")

_OrchestrationResult = tuple[
    dict[str, ProtectionGapItem],
    list[ProtectionRecommendation],
    list[RiskInferred],
    dict[str, ProtectionCalculationStatus],
]


def _coverage_by_category(items: list[ProtectionItem]) -> dict[str, int]:
    """Soma cobertura ativa por categoria (cents)."""
    totals: dict[str, int] = {}
    for it in items:
        totals[it["category"]] = totals.get(it["category"], 0) + int(it["coverage_brl_cents"])
    return totals


def _build_thresholds(inputs: ProtectionComputationInputs) -> ProtectionThresholds:
    us = inputs.us_thresholds
    return ProtectionThresholds(
        life_insurance_multiple_renda_anual=10.0,
        reserva_meses_clt=6,
        reserva_meses_pj=9,
        reserva_meses_socio_variavel=12,
        fbar_threshold_usd=us.fbar_threshold_usd if us else None,
        estate_tax_threshold_usd=us.estate_tax_nra_threshold_usd if us else None,
    )


def _build_gap_life(rec) -> ProtectionGapItem:
    return ProtectionGapItem(
        ideal_brl_cents=rec.ideal_brl_cents,
        actual_brl_cents=rec.actual_brl_cents,
        gap_brl_cents=rec.gap_brl_cents,
        methodology=rec.methodology,
    )


def _build_gap_disability(gap, actual_monthly_cents: int) -> ProtectionGapItem:
    """Para invalidez, ``gap_brl_cents`` representa o anualizado (mensal × 12)."""
    annual_gap = gap.gap_brl_cents_mensal * 12
    return ProtectionGapItem(
        ideal_brl_cents=annual_gap + actual_monthly_cents * 12,
        actual_brl_cents=actual_monthly_cents * 12,
        gap_brl_cents=annual_gap,
        methodology="cerbasi",
    )


def _run_life(
    members: list[FamilyMember],
    today: date,
    coverage_by_cat: dict[str, int],
    effective_date_iso: str,
    computation_inputs: ProtectionComputationInputs,
):
    deps = dependent_ages(members, today)
    assert computation_inputs.annual_active_income_brl_cents is not None
    assert computation_inputs.outstanding_debts_brl_cents is not None
    inputs = LifeInsuranceInputs(
        principal_age=principal_age(members, today),
        dependents_ages=deps.ages,
        annual_active_income_brl_cents=computation_inputs.annual_active_income_brl_cents,
        outstanding_debts_brl_cents=computation_inputs.outstanding_debts_brl_cents,
        current_coverage_brl_cents=coverage_by_cat.get("vida", 0),
        effective_date=effective_date_iso,
    )
    return life_insurance_coverage_ideal(inputs)


def _run_disability(
    items: list[ProtectionItem],
    effective_date_iso: str,
    computation_inputs: ProtectionComputationInputs,
):
    assert computation_inputs.active_net_monthly_income_brl_cents is not None
    assert computation_inputs.passive_net_monthly_income_brl_cents is not None
    actual_monthly = disability_monthly_benefit(items)
    assert actual_monthly is not None
    inputs = DisabilityInputs(
        active_net_monthly_income_brl_cents=computation_inputs.active_net_monthly_income_brl_cents,
        passive_net_monthly_income_brl_cents=computation_inputs.passive_net_monthly_income_brl_cents,
        current_disability_coverage_monthly_brl_cents=actual_monthly,
        effective_date=effective_date_iso,
    )
    return disability_coverage_gap(inputs), actual_monthly


def _run_itcmd(
    effective_date_iso: str,
    computation_inputs: ProtectionComputationInputs,
):
    assert computation_inputs.itcmd_uf is not None
    assert computation_inputs.gross_estate_brl_cents is not None
    assert computation_inputs.itcmd_aliquota_pct_por_uf is not None
    inputs = ITCMDInputs(
        uf=computation_inputs.itcmd_uf,
        gross_estate_brl_cents=computation_inputs.gross_estate_brl_cents,
        effective_date=effective_date_iso,
        aliquota_pct_por_uf=dict(computation_inputs.itcmd_aliquota_pct_por_uf),
    )
    return itcmd_estimated(inputs)


def _run_us_compliance(
    effective_date_iso: str,
    computation_inputs: ProtectionComputationInputs,
) -> list[ComplianceFlag]:
    assert computation_inputs.has_us_assets is not None
    assert computation_inputs.has_us_income is not None
    assert computation_inputs.us_tax_status is not None
    assert computation_inputs.us_assets_usd is not None
    assert computation_inputs.us_thresholds is not None
    inputs = USExposureInputs(
        has_us_assets=computation_inputs.has_us_assets,
        has_us_income=computation_inputs.has_us_income,
        us_tax_status=computation_inputs.us_tax_status,
        us_assets_usd=computation_inputs.us_assets_usd,
        effective_date=effective_date_iso,
        thresholds=computation_inputs.us_thresholds,
    )
    return compliance_risk_us_person(inputs)


def _append_life(life_rec, gap_analysis, recommendations, auto_inferred) -> None:
    if life_rec.ideal_brl_cents > 0 or life_rec.actual_brl_cents > 0:
        gap_analysis["vida"] = _build_gap_life(life_rec)
        recommendations.append(
            ProtectionRecommendation(
                category="vida",
                rationale=life_rec.rationale,
                priority="alta" if life_rec.gap_brl_cents > 0 else "baixa",
            )
        )
    if life_rec.risk_inferred is not None:
        auto_inferred.append(life_rec.risk_inferred)


def _append_disability(
    dis_gap, actual_monthly, gap_analysis, recommendations, auto_inferred
) -> None:
    if dis_gap.gap_brl_cents_mensal > 0 or actual_monthly > 0:
        gap_analysis["invalidez"] = _build_gap_disability(dis_gap, actual_monthly)
        recommendations.append(
            ProtectionRecommendation(
                category="invalidez",
                rationale=dis_gap.rationale,
                priority="alta" if dis_gap.risk_inferred else "baixa",
            )
        )
    if dis_gap.risk_inferred is not None:
        auto_inferred.append(dis_gap.risk_inferred)


def _append_itcmd(itcmd, coverage_by_cat, gap_analysis, recommendations, auto_inferred) -> None:
    if itcmd.itcmd_brl_cents > 0:
        gap_analysis["sucessorio"] = ProtectionGapItem(
            ideal_brl_cents=itcmd.itcmd_brl_cents,
            actual_brl_cents=coverage_by_cat.get("sucessorio", 0),
            gap_brl_cents=max(0, itcmd.itcmd_brl_cents - coverage_by_cat.get("sucessorio", 0)),
            methodology="itcmd",
        )
        recommendations.append(
            ProtectionRecommendation(
                category="sucessorio",
                rationale=itcmd.rationale,
                priority="média",
            )
        )
    if itcmd.risk_inferred is not None:
        auto_inferred.append(itcmd.risk_inferred)


def _append_us_compliance(flags, recommendations, auto_inferred) -> None:
    for flag in flags:
        recommendations.append(
            ProtectionRecommendation(
                category="compliance_us",
                rationale=flag.rationale,
                priority="alta",
            )
        )
        if flag.risk_inferred is not None:
            auto_inferred.append(flag.risk_inferred)


def _log_populated(workspace, items, gap_analysis, auto_inferred, statuses) -> None:
    logger.info(
        "protection_bundle_populated",
        extra={
            "workspace_id": workspace.id if workspace else None,
            "policies_count": len(items),
            "gap_categories": list(gap_analysis.keys()),
            "auto_inferred_count": len(auto_inferred),
            "calculation_status": {key: value["status"] for key, value in statuses.items()},
        },
    )


def _orchestrate_calculators(
    items: list[ProtectionItem],
    members: list[FamilyMember],
    today: date,
    iso: str,
    cov: dict[str, int],
    inputs: ProtectionComputationInputs,
    documentary: DocumentaryCoverage | None = None,
) -> _OrchestrationResult:
    gap: dict[str, ProtectionGapItem] = {}
    recs: list[ProtectionRecommendation] = []
    auto: list[RiskInferred] = []
    statuses = calculation_statuses(members, today, items, inputs, documentary)
    _compute_available_life(statuses, members, today, cov, iso, inputs, gap, recs, auto)
    _compute_available_disability(statuses, items, iso, inputs, gap, recs, auto)
    _compute_available_itcmd(statuses, cov, iso, inputs, gap, recs, auto)
    _compute_available_us(statuses, iso, inputs, recs, auto)
    return gap, recs, auto, statuses


def _compute_available_life(statuses, members, today, cov, iso, inputs, gap, recs, auto):
    if statuses["vida"]["status"] != "computed":
        return
    _append_life(_run_life(members, today, cov, iso, inputs), gap, recs, auto)


def _compute_available_disability(statuses, items, iso, inputs, gap, recs, auto):
    if statuses["invalidez"]["status"] != "computed":
        return
    dis_gap, actual_monthly = _run_disability(items, iso, inputs)
    _append_disability(dis_gap, actual_monthly, gap, recs, auto)


def _compute_available_itcmd(statuses, cov, iso, inputs, gap, recs, auto):
    if statuses["sucessorio"]["status"] != "computed":
        return
    _append_itcmd(_run_itcmd(iso, inputs), cov, gap, recs, auto)


def _compute_available_us(statuses, iso, inputs, recs, auto):
    if statuses["compliance_us"]["status"] != "computed":
        return
    _append_us_compliance(_run_us_compliance(iso, inputs), recs, auto)


def _has_us_exposure(inputs: ProtectionComputationInputs) -> bool | None:
    if inputs.has_us_assets is None or inputs.has_us_income is None or inputs.us_tax_status is None:
        return None
    return bool(inputs.has_us_assets or inputs.has_us_income or inputs.us_tax_status != "none")


def _assemble_bundle(
    items, gap, recs, auto, statuses, inputs, adapter_version, documentary
) -> ProtectionBundle:
    bundle: ProtectionBundle = {
        "policies": items,
        "gap_analysis": gap,
        "recommendations": recs,
        "auto_inferred_risks": auto,
        "calculation_status": statuses,
        "methodology_thresholds": _build_thresholds(inputs),
        "has_us_exposure": _has_us_exposure(inputs),
        "_adapter_version": adapter_version,
    }
    if documentary is not None:
        bundle["documentary_coverage"] = documentary
    return bundle


def populate_protection_bundle(
    *,
    items: list[ProtectionItem],
    members: list[FamilyMember],
    workspace: Optional[Workspace],
    today: date,
    adapter_version: int,
    computation_inputs: ProtectionComputationInputs | None = None,
    documentary_coverage: DocumentaryCoverage | None = None,
) -> ProtectionBundle:
    """Invoca apenas calculators com insumos observados completos."""
    inputs = computation_inputs or ProtectionComputationInputs()
    iso = today.isoformat()
    cov = _coverage_by_category(items)
    gap, recs, auto, statuses = _orchestrate_calculators(
        items, members, today, iso, cov, inputs, documentary_coverage
    )
    _log_populated(workspace, items, gap, auto, statuses)
    return _assemble_bundle(
        items, gap, recs, auto, statuses, inputs, adapter_version, documentary_coverage
    )


__all__ = ["populate_protection_bundle"]
