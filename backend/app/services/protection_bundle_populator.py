"""Populator ``ProtectionBundle`` (ADR-192 §D3, S9-T03) — monta value objects e invoca 4 calculators puros (DIP); thresholds default (ITCMD UF, FBAR/FATCA/Estate Tax) documentados como débito para ``fiscal_parameters`` (ADR-135 follow-up)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from backend.app.core.logging import get_logger
from backend.app.models.family_member import FamilyMember
from backend.app.models.workspace import Workspace
from pipeline.domain.protection_bundle import (
    ProtectionBundle,
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
    USPersonThresholds,
    compliance_risk_us_person,
    disability_coverage_gap,
    itcmd_estimated,
    life_insurance_coverage_ideal,
)

# ITCMD: tabela default de alíquotas por UF (% sobre patrimônio bruto).
# TODO (ADR-135 follow-up): migrar para coluna ``fiscal_parameters.itcmd_aliquota_por_uf``
# (JSON ou tabela filha por vigência) — esta tabela é referência conservadora
# e deve ser refletida em ``fiscal_parameters`` por ``effective_date``.
_ITCMD_ALIQUOTAS_DEFAULT_PCT: dict[str, Decimal] = {
    "AC": Decimal("4"), "AL": Decimal("4"), "AM": Decimal("2"), "AP": Decimal("4"),
    "BA": Decimal("8"), "CE": Decimal("8"), "DF": Decimal("6"), "ES": Decimal("4"),
    "GO": Decimal("8"), "MA": Decimal("7"), "MG": Decimal("5"), "MS": Decimal("6"),
    "MT": Decimal("8"), "PA": Decimal("4"), "PB": Decimal("8"), "PE": Decimal("8"),
    "PI": Decimal("6"), "PR": Decimal("4"), "RJ": Decimal("8"), "RN": Decimal("6"),
    "RO": Decimal("4"), "RR": Decimal("4"), "RS": Decimal("6"), "SC": Decimal("8"),
    "SE": Decimal("8"), "SP": Decimal("4"), "TO": Decimal("4"),
}  # fmt: skip

# US compliance: thresholds default.
# TODO (ADR-135 follow-up): migrar para ``fiscal_parameters.us_thresholds_usd`` por vigência.
_US_THRESHOLDS_DEFAULT: USPersonThresholds = USPersonThresholds(
    fbar_threshold_usd=10_000,
    fatca_single_threshold_usd=50_000,
    fatca_joint_threshold_usd=100_000,
    estate_tax_nra_threshold_usd=60_000,
)

# Codes ``us_tax_status`` que representam pessoa fiscalmente americana.
_US_PERSON_CODES: frozenset[str] = frozenset(
    {"resident", "former_resident_within_10y", "greencard_expiring", "citizen"}
)

logger = get_logger("mathoms.protection.populator")


def _coverage_by_category(items: list[ProtectionItem]) -> dict[str, int]:
    """Soma cobertura ativa por categoria (cents)."""
    totals: dict[str, int] = {}
    for it in items:
        totals[it["category"]] = totals.get(it["category"], 0) + int(it["coverage_brl_cents"])
    return totals


def _disability_coverage_monthly(items: list[ProtectionItem]) -> int:
    """Proxy mensal de cobertura de invalidez (refinamento real em T-futuro)."""
    cat_total = sum(int(it["coverage_brl_cents"]) for it in items if it["category"] == "invalidez")
    return (cat_total // 12) if cat_total > 0 else 0


def _age_from_birth(
    birth: Optional[date] = None, reference: Optional[date] = None
) -> Optional[int]:
    if birth is None or reference is None:
        return None
    age = (
        reference.year - birth.year - ((reference.month, reference.day) < (birth.month, birth.day))
    )
    return max(0, age)


def _has_us_exposure(members: list[FamilyMember], workspace: Optional[Workspace] = None) -> bool:
    """``has_us_exposure`` (ADR-192 §D4) derivado de ``family_members`` + workspace flag."""
    for m in members:
        status = getattr(m, "us_tax_status", None)
        if status and status in _US_PERSON_CODES:
            return True
    if workspace is not None and workspace.business_profile_json:
        bp = workspace.business_profile_json
        if isinstance(bp, dict) and bool(bp.get("us_exposure_explicit", False)):
            return True
    return False


def _titular_us_tax_status(members: list[FamilyMember]) -> str:
    """Status do titular ou primeiro membro disponível."""
    for m in members:
        if m.role == "titular":
            return getattr(m, "us_tax_status", None) or "none"
    if members:
        return getattr(members[0], "us_tax_status", None) or "none"
    return "none"


def _dependents_ages(members: list[FamilyMember], today: date) -> tuple[int, ...]:
    ages = [_age_from_birth(m.birth_date, today) for m in members if m.role == "dependente"]
    return tuple(a for a in ages if a is not None)


def _principal_age(members: list[FamilyMember], today: date) -> int:
    titulares = [m for m in members if m.role == "titular"]
    ages = [_age_from_birth(m.birth_date, today) for m in titulares]
    valid = [a for a in ages if a is not None]
    return valid[0] if valid else 0


def _resolve_uf(workspace: Optional[Workspace] = None) -> str:
    """UF do titular via ``business_profile_json.uf_titular`` ou fallback SP."""
    if workspace is None or not workspace.business_profile_json:
        return "SP"
    bp = workspace.business_profile_json
    if isinstance(bp, dict):
        return str(bp.get("uf_titular") or "SP").upper()
    return "SP"


def _build_thresholds() -> ProtectionThresholds:
    """Snapshot dos thresholds default — exposto via bundle (UI consome)."""
    return ProtectionThresholds(
        life_insurance_multiple_renda_anual=10.0,
        reserva_meses_clt=6,
        reserva_meses_pj=9,
        reserva_meses_socio_variavel=12,
        fbar_threshold_usd=_US_THRESHOLDS_DEFAULT.fbar_threshold_usd,
        estate_tax_threshold_usd=_US_THRESHOLDS_DEFAULT.estate_tax_nra_threshold_usd,
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
):
    """Roda calculator de vida; retorna recomendação ou None."""
    deps_ages = _dependents_ages(members, today)
    inputs = LifeInsuranceInputs(
        principal_age=_principal_age(members, today),
        dependents_ages=deps_ages,
        annual_active_income_brl_cents=0,  # TODO: do baseline/E5
        outstanding_debts_brl_cents=0,  # TODO: do baseline E1.5
        current_coverage_brl_cents=coverage_by_cat.get("vida", 0),
        effective_date=effective_date_iso,
    )
    return life_insurance_coverage_ideal(inputs)


def _run_disability(items: list[ProtectionItem], effective_date_iso: str):
    actual_monthly = _disability_coverage_monthly(items)
    inputs = DisabilityInputs(
        active_net_monthly_income_brl_cents=0,  # TODO: do E5/IRPF
        passive_net_monthly_income_brl_cents=0,
        current_disability_coverage_monthly_brl_cents=actual_monthly,
        effective_date=effective_date_iso,
    )
    return disability_coverage_gap(inputs), actual_monthly


def _run_itcmd(
    workspace: Optional[Workspace],  # pode ser None em testes/workspace recém-criado
    effective_date_iso: str,
):
    inputs = ITCMDInputs(
        uf=_resolve_uf(workspace),
        gross_estate_brl_cents=0,  # TODO: do baseline E1.5
        effective_date=effective_date_iso,
        aliquota_pct_por_uf=_ITCMD_ALIQUOTAS_DEFAULT_PCT,
    )
    return itcmd_estimated(inputs)


def _run_us_compliance(
    members: list[FamilyMember], effective_date_iso: str
) -> list[ComplianceFlag]:
    inputs = USExposureInputs(
        has_us_assets=False,  # TODO: campo no business_profile_json
        has_us_income=False,
        us_tax_status=_titular_us_tax_status(members),  # type: ignore[arg-type]
        us_assets_usd=None,
        effective_date=effective_date_iso,
        thresholds=_US_THRESHOLDS_DEFAULT,
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


def _log_populated(workspace, items, gap_analysis, auto_inferred, has_us_exposure) -> None:
    logger.info(
        "protection_bundle_populated",
        extra={
            "workspace_id": workspace.id if workspace else None,
            "policies_count": len(items),
            "gap_categories": list(gap_analysis.keys()),
            "auto_inferred_count": len(auto_inferred),
            "has_us_exposure": has_us_exposure,
        },
    )


def _orchestrate_calculators(
    items: list[ProtectionItem],
    members: list[FamilyMember],
    workspace: Optional[Workspace],  # populator chain — pode ser None em testes
    today: date,
    iso: str,
    cov: dict[str, int],
    has_us: bool,
) -> tuple[dict[str, ProtectionGapItem], list[ProtectionRecommendation], list[RiskInferred]]:
    """Roda os 4 calculators e agrega resultados; chamada pelo populator."""
    gap: dict[str, ProtectionGapItem] = {}
    recs: list[ProtectionRecommendation] = []
    auto: list[RiskInferred] = []
    _append_life(_run_life(members, today, cov, iso), gap, recs, auto)
    dis_gap, actual_monthly = _run_disability(items, iso)
    _append_disability(dis_gap, actual_monthly, gap, recs, auto)
    _append_itcmd(_run_itcmd(workspace, iso), cov, gap, recs, auto)
    if has_us:
        _append_us_compliance(_run_us_compliance(members, iso), recs, auto)
    return gap, recs, auto


def _assemble_bundle(items, gap_analysis, recs, auto, has_us, adapter_version) -> ProtectionBundle:
    return {
        "policies": items,
        "gap_analysis": gap_analysis,
        "recommendations": recs,
        "auto_inferred_risks": auto,
        "methodology_thresholds": _build_thresholds(),
        "has_us_exposure": has_us,
        "_adapter_version": adapter_version,
    }


def populate_protection_bundle(
    *,
    items: list[ProtectionItem],
    members: list[FamilyMember],
    workspace: Optional[Workspace],
    today: date,
    adapter_version: int,
) -> ProtectionBundle:
    """Popula ``ProtectionBundle`` (ADR-192 §D3, T03) invocando 4 calculators puros."""
    has_us = _has_us_exposure(members, workspace)
    iso = today.isoformat()
    cov = _coverage_by_category(items)
    gap, recs, auto = _orchestrate_calculators(items, members, workspace, today, iso, cov, has_us)
    _log_populated(workspace, items, gap, auto, has_us)
    return _assemble_bundle(items, gap, recs, auto, has_us, adapter_version)


__all__ = ["populate_protection_bundle"]
