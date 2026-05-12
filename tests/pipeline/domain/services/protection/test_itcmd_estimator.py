"""Testes ``itcmd_estimated`` (ADR-192 §D3, S9-T03)."""

from __future__ import annotations

from decimal import Decimal

from pipeline.domain.services.protection.itcmd_estimator import (
    ITCMDInputs,
    itcmd_estimated,
)
from pipeline.domain.services.protection.risk_inferred import SOURCE_CALCULATORS_WHITELIST

_EFFECTIVE_DATE = "2026-05-12"

_ALIQUOTAS_TEST = {
    "SP": Decimal("4"),
    "RJ": Decimal("8"),
    "MG": Decimal("5"),
}


def _inputs(**overrides) -> ITCMDInputs:
    defaults = dict(
        uf="SP",
        gross_estate_brl_cents=0,
        effective_date=_EFFECTIVE_DATE,
        aliquota_pct_por_uf=_ALIQUOTAS_TEST,
    )
    defaults.update(overrides)
    return ITCMDInputs(**defaults)


def test_solteiro_sp_patrimonio_zero_nao_emite() -> None:
    out = itcmd_estimated(_inputs())
    assert out.itcmd_brl_cents == 0
    assert out.risk_inferred is None


def test_casado_mg_patrimonio_2m_aliquota_5pct() -> None:
    """MG 5%: 2M × 5% = R$ 100k."""
    out = itcmd_estimated(_inputs(uf="MG", gross_estate_brl_cents=2_000_000_00))
    assert out.aliquota_pct == Decimal("5")
    assert out.itcmd_brl_cents == 100_000_00  # R$ 100k
    assert out.risk_inferred is not None
    assert out.risk_inferred["source_calculator"] == "itcmd_estimated"
    assert out.risk_inferred["source_calculator"] in SOURCE_CALCULATORS_WHITELIST


def test_expatriado_rj_patrimonio_alto_aliquota_8pct() -> None:
    """RJ 8%: 5M × 8% = R$ 400k."""
    out = itcmd_estimated(_inputs(uf="RJ", gross_estate_brl_cents=5_000_000_00))
    assert out.aliquota_pct == Decimal("8")
    assert out.itcmd_brl_cents == 400_000_00
    assert out.risk_inferred is not None
    assert out.risk_inferred["category"] == "sucessorio"


def test_uf_nao_mapeada_degrada_graciosamente() -> None:
    """UF fora da tabela: itcmd=0, alíquota=0, sem risk."""
    out = itcmd_estimated(_inputs(uf="ZZ", gross_estate_brl_cents=1_000_000_00))
    assert out.aliquota_pct == Decimal("0")
    assert out.itcmd_brl_cents == 0
    assert out.risk_inferred is None
    assert "ZZ" in out.rationale
    assert "não encontrada" in out.rationale


def test_uf_lowercase_normaliza_para_uppercase() -> None:
    out = itcmd_estimated(_inputs(uf="sp", gross_estate_brl_cents=1_000_000_00))
    assert out.uf == "SP"
    assert out.aliquota_pct == Decimal("4")


def test_itcmd_imaterial_nao_emite_risk() -> None:
    """ITCMD < R$ 10k: estimativa irrelevante, não polui auto_inferred."""
    # SP 4%: patrimônio = R$ 200k → ITCMD = R$ 8k.
    out = itcmd_estimated(_inputs(uf="SP", gross_estate_brl_cents=200_000_00))
    assert out.itcmd_brl_cents == 8_000_00
    assert out.risk_inferred is None  # < 10k


def test_disclaimer_presente_no_rationale() -> None:
    out = itcmd_estimated(_inputs(uf="SP", gross_estate_brl_cents=1_000_000_00))
    assert "não constitui recomendação fiduciária" in out.rationale
    assert "Susep" in out.rationale
    assert _EFFECTIVE_DATE in out.rationale


def test_idempotente() -> None:
    inputs = _inputs(uf="SP", gross_estate_brl_cents=1_000_000_00)
    o1 = itcmd_estimated(inputs)
    o2 = itcmd_estimated(inputs)
    assert o1 == o2


def test_patrimonio_negativo_zera() -> None:
    out = itcmd_estimated(_inputs(gross_estate_brl_cents=-1))
    assert out.itcmd_brl_cents == 0
