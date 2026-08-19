"""Computabilidade por categoria de proteção (ADR-387 §D3/§D4; ADR-395 §D2).

Extraído de ``protection_bundle_populator`` em A40.l73 — o populator orquestra
calculators, este módulo decide **se** cada categoria pode ser calculada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, Optional

from backend.app.models.family_member import FamilyMember
from backend.app.services.protection_bundle_inputs import ProtectionComputationInputs
from pipeline.domain.protection_bundle import (
    DocumentaryCoverage,
    ProtectionCalculationStatus,
    ProtectionItem,
)


@dataclass(frozen=True)
class DependentAgesResolution:
    status: Literal["confirmed", "none", "indeterminate"]
    ages: tuple[int, ...] = ()


def _age_from_birth(
    birth: Optional[date] = None, reference: Optional[date] = None
) -> Optional[int]:
    if birth is None or reference is None:
        return None
    if birth > reference:
        return None
    age = (
        reference.year - birth.year - ((reference.month, reference.day) < (birth.month, birth.day))
    )
    return age


def dependent_ages(members: list[FamilyMember], today: date) -> DependentAgesResolution:
    eligible = [member for member in members if member.role in {"filho", "dependente"}]
    if not members:
        return DependentAgesResolution("indeterminate")
    if not eligible:
        return DependentAgesResolution("none")
    ages = [_age_from_birth(member.birth_date, today) for member in eligible]
    if any(age is None for age in ages):
        return DependentAgesResolution("indeterminate")
    if any(member.role == "dependente" and age >= 18 for member, age in zip(eligible, ages)):
        return DependentAgesResolution("indeterminate")
    minors = tuple(age for age in ages if age < 18)
    return (
        DependentAgesResolution("confirmed", minors) if minors else DependentAgesResolution("none")
    )


def principal_age(members: list[FamilyMember], today: date) -> int:
    titulares = [m for m in members if m.role == "titular"]
    ages = [_age_from_birth(m.birth_date, today) for m in titulares]
    valid = [a for a in ages if a is not None]
    return valid[0] if valid else 0


def disability_monthly_benefit(items: list[ProtectionItem]) -> int | None:
    """Soma só benefício mensal contratual; capital único não vira renda (ADR-387 D6)."""
    monthly = 0
    for item in items:
        if item["category"] != "invalidez":
            continue
        if item.get("benefit_mode") != "monthly_income":
            return None
        benefit = item.get("benefit_monthly_brl_cents")
        if benefit is None:
            return None
        monthly += int(benefit)
    return monthly


def _status(
    state: Literal["computed", "not_applicable", "missing_data"],
    *,
    missing: tuple[str, ...] = (),
    reason: str,
) -> ProtectionCalculationStatus:
    return ProtectionCalculationStatus(status=state, missing_inputs=list(missing), reason=reason)


def _missing_names(*candidates: tuple[str, object | None]) -> tuple[str, ...]:
    return tuple(name for name, value in candidates if value is None)


def _life_status(
    members: list[FamilyMember], today: date, inputs: ProtectionComputationInputs
) -> ProtectionCalculationStatus:
    deps = dependent_ages(members, today)
    if deps.status == "none":
        return _status("not_applicable", reason="Nenhum dependente econômico menor confirmado.")
    if deps.status == "indeterminate":
        return _status(
            "missing_data",
            missing=("dependents_ages",),
            reason="Idade ou dependência econômica não confirmada.",
        )
    missing = _missing_names(
        ("annual_active_income_brl_cents", inputs.annual_active_income_brl_cents),
        ("outstanding_debts_brl_cents", inputs.outstanding_debts_brl_cents),
    )
    if missing:
        return _status("missing_data", missing=missing, reason="Renda ativa ou dívida ausente.")
    return _status("computed", reason="Calculado sobre dependentes e insumos observados.")


def _disability_status(
    items: list[ProtectionItem], inputs: ProtectionComputationInputs
) -> ProtectionCalculationStatus:
    missing = _missing_names(
        ("active_net_monthly_income_brl_cents", inputs.active_net_monthly_income_brl_cents),
        ("passive_net_monthly_income_brl_cents", inputs.passive_net_monthly_income_brl_cents),
    )
    if missing:
        return _status(
            "missing_data", missing=missing, reason="Par de renda líquida mensal incompleto."
        )
    if disability_monthly_benefit(items) is None:
        return _status(
            "missing_data",
            missing=("disability_monthly_benefit",),
            reason="Capital único de invalidez não se converte em renda mensal.",
        )
    return _status("computed", reason="Calculado sobre rendas líquidas da mesma base.")


def _itcmd_status(inputs: ProtectionComputationInputs) -> ProtectionCalculationStatus:
    missing = _missing_names(
        ("gross_estate_brl_cents", inputs.gross_estate_brl_cents),
        ("itcmd_uf", inputs.itcmd_uf),
        ("itcmd_aliquota_pct_por_uf", inputs.itcmd_aliquota_pct_por_uf),
    )
    if missing:
        return _status(
            "missing_data", missing=missing, reason="Patrimônio, UF ou parâmetro fiscal ausente."
        )
    if inputs.itcmd_uf.upper() not in inputs.itcmd_aliquota_pct_por_uf:
        return _status(
            "missing_data",
            missing=("itcmd_aliquota_pct_por_uf",),
            reason="Não há alíquota vigente para a UF observada.",
        )
    return _status("computed", reason="Calculado com patrimônio bruto e parâmetro vigente.")


def _us_status(inputs: ProtectionComputationInputs) -> ProtectionCalculationStatus:
    evidence_missing = _missing_us_evidence(inputs)
    if evidence_missing:
        return _status(
            "missing_data", missing=evidence_missing, reason="Evidência de exposição EUA ausente."
        )
    if _explicitly_no_us_exposure(inputs):
        return _status("not_applicable", reason="Ausência explícita de exposição fiscal EUA.")
    missing = _missing_names(
        ("us_assets_usd", inputs.us_assets_usd),
        ("us_thresholds", inputs.us_thresholds),
    )
    if missing:
        return _status("missing_data", missing=missing, reason="Valor ou thresholds EUA ausentes.")
    return _status(
        "missing_data",
        missing=("compliance_us_rule",),
        reason="Regra atual não modela renda EUA sem afirmar filing indevido.",
    )


def _explicitly_no_us_exposure(inputs: ProtectionComputationInputs) -> bool:
    return not inputs.has_us_assets and not inputs.has_us_income and inputs.us_tax_status == "none"


def _missing_us_evidence(inputs: ProtectionComputationInputs) -> tuple[str, ...]:
    return _missing_names(
        ("has_us_assets", inputs.has_us_assets),
        ("has_us_income", inputs.has_us_income),
        ("us_tax_status", inputs.us_tax_status),
    )


# ADR-395 §D2 — apólice vigente em documento sem par ativo no cadastro é
# contraprova de que o inventário do cadastro está incompleto. Retido não
# computa, logo o populator não emite gap, conselho nem risco na categoria.
def _retain_documentary_unconfirmed(
    statuses: dict[str, ProtectionCalculationStatus],
    documentary: DocumentaryCoverage | None = None,
) -> None:
    for category in (documentary or {}).get("unconfirmed_categories", []):
        if category not in statuses:
            continue
        statuses[category] = _status(
            "missing_data",
            missing=("policy_inventory_confirmation",),
            reason="Cobertura identificada em documento, não confirmada no cadastro.",
        )


def calculation_statuses(
    members: list[FamilyMember],
    today: date,
    items: list[ProtectionItem],
    inputs: ProtectionComputationInputs,
    documentary: DocumentaryCoverage | None = None,
) -> dict[str, ProtectionCalculationStatus]:
    """Computabilidade por categoria, já com a retenção documental aplicada."""
    statuses = {
        "vida": _life_status(members, today, inputs),
        "invalidez": _disability_status(items, inputs),
        "sucessorio": _itcmd_status(inputs),
        "compliance_us": _us_status(inputs),
    }
    _retain_documentary_unconfirmed(statuses, documentary)
    return statuses


__all__ = [
    "DependentAgesResolution",
    "calculation_statuses",
    "dependent_ages",
    "principal_age",
    "disability_monthly_benefit",
]
