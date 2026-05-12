"""Calculator ``compliance_risk_us_person`` (ADR-192 §D3, S9-T03) — flags FBAR/FATCA/Estate Tax NRA. Gate explícito: ``us_tax_status`` ≠ ``none`` OU ``has_us_assets AND us_assets > FBAR``. Thresholds injetados pelo adapter (ADR-135). Boundary ADR-101 R5; USD em int (sem ``Money.brl`` nesta camada)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from pipeline.domain.protection_bundle import RiskInferred
from pipeline.domain.services.protection.disclaimer import render_disclaimer
from pipeline.domain.services.protection.risk_inferred import build_risk_inferred

USTaxStatus = Literal[
    "none",
    "resident",
    "former_resident_within_10y",
    "greencard_expiring",
    "citizen",
]

_VALID_US_TAX_STATUSES: frozenset[str] = frozenset(
    {"none", "resident", "former_resident_within_10y", "greencard_expiring", "citizen"}
)


@dataclass(frozen=True)
class USPersonThresholds:
    """Thresholds injetados pelo adapter via ``fiscal_parameters`` (ADR-135)."""

    fbar_threshold_usd: int  # típico: 10_000
    fatca_single_threshold_usd: int  # típico: 50_000 (resident) / 200_000 (expat)
    fatca_joint_threshold_usd: int  # típico: 100_000 (resident) / 400_000 (expat)
    estate_tax_nra_threshold_usd: int  # non-resident alien: 60_000 federal


@dataclass(frozen=True)
class USExposureInputs:
    """Inputs tipados para ``compliance_risk_us_person`` (ADR-097 D2/D3)."""

    has_us_assets: bool
    has_us_income: bool
    us_tax_status: USTaxStatus
    us_assets_usd: Optional[int]
    effective_date: str
    thresholds: USPersonThresholds


@dataclass(frozen=True)
class ComplianceFlag:
    """Flag de compliance emitida pelo calculator (uma por rule disparada)."""

    code: str
    name: str
    threshold_usd: int
    rationale: str
    risk_inferred: Optional[RiskInferred] = None


def _us_person_active(us_tax_status: str) -> bool:
    """``us_tax_status`` representa pessoa fiscalmente americana?"""
    return us_tax_status in {
        "resident",
        "former_resident_within_10y",
        "greencard_expiring",
        "citizen",
    }


def _build_flag(
    *, code: str, name: str, threshold_usd: int, rationale: str, risk_name: str
) -> ComplianceFlag:
    risk = build_risk_inferred(
        category="compliance_us",
        name=risk_name,
        rationale=rationale,
        source_calculator="compliance_risk_us_person",
    )
    return ComplianceFlag(
        code=code, name=name, threshold_usd=threshold_usd, rationale=rationale, risk_inferred=risk
    )


def _fbar_flag(inputs: USExposureInputs, us_assets: int, disclaimer: str) -> ComplianceFlag:
    threshold = inputs.thresholds.fbar_threshold_usd
    assets_str = f"USD {us_assets:_.0f}".replace("_", ",")
    threshold_str = f"USD {threshold:_.0f}".replace("_", ",")
    rationale = (
        f"Status fiscal: {inputs.us_tax_status}; ativos declarados nos EUA: {assets_str}. "
        f"FBAR (FinCEN Form 114) obrigatório quando soma de contas estrangeiras "
        f"excede {threshold_str} em qualquer momento do ano-calendário. {disclaimer}"
    )
    return _build_flag(
        code="FBAR",
        name="FBAR obrigatório (FinCEN Form 114)",
        threshold_usd=threshold,
        rationale=rationale,
        risk_name="compliance_us_fbar",
    )


def _fatca_flag(inputs: USExposureInputs, disclaimer: str) -> ComplianceFlag:
    threshold = inputs.thresholds.fatca_single_threshold_usd
    threshold_str = f"USD {threshold:_.0f}".replace("_", ",")
    rationale = (
        f"Ativos estrangeiros (Form 8938) excedem threshold de {threshold_str} "
        f"para US-person ({inputs.us_tax_status}). "
        f"Submeter Form 8938 anual junto à declaração 1040. {disclaimer}"
    )
    return _build_flag(
        code="FATCA",
        name="FATCA Form 8938 obrigatório",
        threshold_usd=threshold,
        rationale=rationale,
        risk_name="compliance_us_fatca",
    )


def _estate_tax_nra_flag(
    inputs: USExposureInputs, us_assets: int, disclaimer: str
) -> ComplianceFlag:
    threshold = inputs.thresholds.estate_tax_nra_threshold_usd
    assets_str = f"USD {us_assets:_.0f}".replace("_", ",")
    threshold_str = f"USD {threshold:_.0f}".replace("_", ",")
    rationale = (
        f"Non-resident alien com ativos US-situs em {assets_str} excede threshold federal "
        f"de {threshold_str}. Estate Tax federal (40%) incide sobre US-situs assets em "
        f"transmissão causa mortis; planejar mitigação (LLC, ITF, situs offshore). {disclaimer}"
    )
    return _build_flag(
        code="ESTATE_TAX_NRA",
        name="Estate Tax (non-resident alien)",
        threshold_usd=threshold,
        rationale=rationale,
        risk_name="compliance_us_estate_tax_nra",
    )


def _should_emit(us_person: bool, has_assets: bool, us_assets: int, fbar: int) -> bool:
    """Gate ADR-192 §D3."""
    return us_person or (has_assets and us_assets > fbar)


def _validate_status(us_tax_status: str) -> None:
    if us_tax_status not in _VALID_US_TAX_STATUSES:
        raise ValueError(
            f"us_tax_status inválido: {us_tax_status!r}. Aceitos: {sorted(_VALID_US_TAX_STATUSES)}"
        )


def _collect_flags(
    inputs: USExposureInputs, us_person: bool, us_assets: int, has_assets: bool, disclaimer: str
) -> list[ComplianceFlag]:
    th = inputs.thresholds
    flags: list[ComplianceFlag] = []
    if us_person or us_assets > th.fbar_threshold_usd:
        flags.append(_fbar_flag(inputs, us_assets, disclaimer))
    if us_person and us_assets > th.fatca_single_threshold_usd:
        flags.append(_fatca_flag(inputs, disclaimer))
    if (
        inputs.us_tax_status == "none"
        and has_assets
        and us_assets > th.estate_tax_nra_threshold_usd
    ):
        flags.append(_estate_tax_nra_flag(inputs, us_assets, disclaimer))
    return flags


def compliance_risk_us_person(inputs: USExposureInputs) -> list[ComplianceFlag]:
    """Lista de flags compliance US-person (ADR-192 §D3); puro, idempotente (ADR-111)."""
    _validate_status(inputs.us_tax_status)
    us_person = _us_person_active(inputs.us_tax_status)
    us_assets = inputs.us_assets_usd or 0
    has_assets = bool(inputs.has_us_assets) and us_assets > 0
    if not _should_emit(us_person, has_assets, us_assets, inputs.thresholds.fbar_threshold_usd):
        return []
    disclaimer = render_disclaimer(
        sources="FBAR/FATCA/Estate Tax (fiscal_parameters)",
        effective_date=inputs.effective_date,
    )
    return _collect_flags(inputs, us_person, us_assets, has_assets, disclaimer)


__all__ = [
    "ComplianceFlag",
    "USExposureInputs",
    "USPersonThresholds",
    "USTaxStatus",
    "compliance_risk_us_person",
]
