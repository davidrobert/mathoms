"""Calculator ``itcmd_estimated`` (ADR-192 §D3, S9-T03) — ITCMD por UF = patrimônio × alíquota. Tabela injetada pelo adapter via ``fiscal_parameters`` (ADR-135 / ADR-192 §"Atualizações pós-revisão"). Pure (ADR-097 D3 / ADR-111). Boundary ADR-101 R5; cents int64 (ADR-090)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from pipeline.domain.protection_bundle import RiskInferred
from pipeline.domain.services.protection.disclaimer import render_disclaimer
from pipeline.domain.services.protection.risk_inferred import build_risk_inferred


@dataclass(frozen=True)
class ITCMDInputs:
    """Inputs tipados para ``itcmd_estimated`` (ADR-097 D2/D3); ``aliquota_pct_por_uf`` injetado pelo adapter."""

    uf: str
    gross_estate_brl_cents: int
    effective_date: str
    aliquota_pct_por_uf: dict[str, Decimal]


@dataclass(frozen=True)
class ITCMDEstimate:
    """Output do calculator de ITCMD."""

    itcmd_brl_cents: int
    aliquota_pct: Decimal
    uf: str
    effective_date: str
    rationale: str
    risk_inferred: Optional[RiskInferred] = None


def _format_brl(cents: int) -> str:
    reais = cents // 100
    return f"R$ {reais:_.0f}".replace("_", ".")


def _itcmd_uf_unknown(uf: str, effective_date: str) -> ITCMDEstimate:
    """UF fora da tabela: degrada para 0 com warning textual no rationale."""
    disclaimer = render_disclaimer(
        sources="Tabela ITCMD estadual (fiscal_parameters)",
        effective_date=effective_date,
    )
    rationale = (
        f"UF '{uf}' não encontrada na tabela de alíquotas vigente em "
        f"{effective_date}; estimativa indisponível. "
        f"Cadastrar UF do titular para cálculo. {disclaimer}"
    )
    return ITCMDEstimate(
        itcmd_brl_cents=0,
        aliquota_pct=Decimal("0"),
        uf=uf,
        effective_date=effective_date,
        rationale=rationale,
        risk_inferred=None,
    )


def _itcmd_rationale(gross: int, uf: str, aliquota: Decimal, itcmd: int, disclaimer: str) -> str:
    return (
        f"Patrimônio bruto declarado: {_format_brl(gross)}; "
        f"alíquota ITCMD-{uf} vigente: {aliquota}%; "
        f"ITCMD estimado: {_format_brl(itcmd)}. "
        f"Não inclui doações em vida nem deduções (cônjuge meeiro, dependentes). "
        f"{disclaimer}"
    )


def _itcmd_risk(itcmd_cents: int, rationale: str):
    """Material > R$ 10k justifica revisão sucessória."""
    if itcmd_cents <= 10_000_00:
        return None
    return build_risk_inferred(
        category="sucessorio",
        name="sucessorio_itcmd_estimado",
        rationale=rationale,
        estimated_impact_brl_cents=itcmd_cents,
        source_calculator="itcmd_estimated",
    )


def _build_itcmd_estimate(
    uf: str, aliquota: Decimal, gross: int, itcmd: int, effective_date: str
) -> ITCMDEstimate:
    disclaimer = render_disclaimer(
        sources=f"Tabela ITCMD {uf} (fiscal_parameters)", effective_date=effective_date
    )
    rationale = _itcmd_rationale(gross, uf, aliquota, itcmd, disclaimer)
    return ITCMDEstimate(
        itcmd_brl_cents=itcmd,
        aliquota_pct=aliquota,
        uf=uf,
        effective_date=effective_date,
        rationale=rationale,
        risk_inferred=_itcmd_risk(itcmd, rationale),
    )


def itcmd_estimated(inputs: ITCMDInputs) -> ITCMDEstimate:
    """ITCMD = ``patrimônio_bruto × alíquota_uf`` (ADR-192 §D3); puro, idempotente."""
    uf = inputs.uf.upper().strip()
    aliquota = inputs.aliquota_pct_por_uf.get(uf)
    if aliquota is None:
        return _itcmd_uf_unknown(uf, inputs.effective_date)
    gross = max(0, inputs.gross_estate_brl_cents)
    itcmd = int((Decimal(gross) * aliquota / Decimal("100")).to_integral_value())
    return _build_itcmd_estimate(uf, aliquota, gross, itcmd, inputs.effective_date)


__all__ = ["ITCMDEstimate", "ITCMDInputs", "itcmd_estimated"]
