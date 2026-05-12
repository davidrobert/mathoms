"""Testes ``compliance_risk_us_person`` (ADR-192 §D3, S9-T03)."""

from __future__ import annotations

import pytest

from pipeline.domain.services.protection.compliance_us_person import (
    USExposureInputs,
    USPersonThresholds,
    compliance_risk_us_person,
)
from pipeline.domain.services.protection.risk_inferred import SOURCE_CALCULATORS_WHITELIST

_EFFECTIVE_DATE = "2026-05-12"
_TH = USPersonThresholds(
    fbar_threshold_usd=10_000,
    fatca_single_threshold_usd=50_000,
    fatca_joint_threshold_usd=100_000,
    estate_tax_nra_threshold_usd=60_000,
)


def _inputs(**overrides) -> USExposureInputs:
    defaults = dict(
        has_us_assets=False,
        has_us_income=False,
        us_tax_status="none",
        us_assets_usd=None,
        effective_date=_EFFECTIVE_DATE,
        thresholds=_TH,
    )
    defaults.update(overrides)
    return USExposureInputs(**defaults)


def test_solteiro_brasileiro_sem_exposicao_nao_emite_flag() -> None:
    """ADR-192 §contexto: NÃO assumir 'CPA expatriado'."""
    flags = compliance_risk_us_person(_inputs())
    assert flags == []


def test_casado_brasileiro_com_pouca_grana_nos_eua_sem_fbar() -> None:
    """USD 5k < FBAR threshold 10k → não dispara."""
    flags = compliance_risk_us_person(_inputs(has_us_assets=True, us_assets_usd=5_000))
    assert flags == []


def test_brasileiro_com_us_assets_acima_fbar_emite_apenas_fbar() -> None:
    """Non-resident sem us_tax_status='none' formal mas com ativos acima FBAR."""
    flags = compliance_risk_us_person(_inputs(has_us_assets=True, us_assets_usd=20_000))
    codes = [f.code for f in flags]
    assert "FBAR" in codes
    # Não é US-person → não dispara FATCA.
    assert "FATCA" not in codes
    # Ativos < 60k → não dispara Estate Tax NRA.
    assert "ESTATE_TAX_NRA" not in codes


def test_brasileiro_com_us_assets_acima_60k_emite_estate_tax_nra() -> None:
    flags = compliance_risk_us_person(_inputs(has_us_assets=True, us_assets_usd=80_000))
    codes = [f.code for f in flags]
    assert "FBAR" in codes
    assert "ESTATE_TAX_NRA" in codes


def test_us_citizen_sem_ativos_ainda_emite_fbar() -> None:
    """US citizen sempre tem obrigação reportar (FBAR), mesmo sem ativos relevantes."""
    flags = compliance_risk_us_person(_inputs(us_tax_status="citizen"))
    codes = [f.code for f in flags]
    assert "FBAR" in codes


def test_expatriado_recente_com_ativos_acima_fatca_emite_3_flags() -> None:
    """Former resident within 10y + USD 80k → FBAR + FATCA."""
    flags = compliance_risk_us_person(
        _inputs(
            has_us_assets=True,
            us_tax_status="former_resident_within_10y",
            us_assets_usd=80_000,
        )
    )
    codes = [f.code for f in flags]
    assert "FBAR" in codes
    assert "FATCA" in codes
    # Estate Tax NRA exige us_tax_status="none" — não dispara para former resident.
    assert "ESTATE_TAX_NRA" not in codes


def test_greencard_expirando_dispara_fbar_se_us_person() -> None:
    flags = compliance_risk_us_person(_inputs(us_tax_status="greencard_expiring"))
    codes = [f.code for f in flags]
    assert "FBAR" in codes


def test_todas_flags_carregam_disclaimer_e_source_calculator() -> None:
    flags = compliance_risk_us_person(
        _inputs(
            has_us_assets=True,
            us_tax_status="resident",
            us_assets_usd=200_000,
        )
    )
    assert len(flags) >= 2  # FBAR + FATCA
    for f in flags:
        assert "não constitui recomendação fiduciária" in f.rationale
        assert "Susep" in f.rationale
        assert _EFFECTIVE_DATE in f.rationale
        assert f.risk_inferred is not None
        assert f.risk_inferred["source_calculator"] == "compliance_risk_us_person"
        assert f.risk_inferred["source_calculator"] in SOURCE_CALCULATORS_WHITELIST


def test_us_tax_status_invalido_levanta_value_error() -> None:
    with pytest.raises(ValueError, match="us_tax_status inválido"):
        compliance_risk_us_person(_inputs(us_tax_status="alien_visitor"))  # type: ignore[arg-type]


def test_idempotente() -> None:
    inputs = _inputs(has_us_assets=True, us_tax_status="resident", us_assets_usd=100_000)
    f1 = compliance_risk_us_person(inputs)
    f2 = compliance_risk_us_person(inputs)
    assert f1 == f2


def test_riscos_inferidos_apenas_compliance_us_categoria() -> None:
    """Whitelist: source_calculator das flags é o compliance_risk_us_person."""
    flags = compliance_risk_us_person(
        _inputs(us_tax_status="citizen", has_us_assets=True, us_assets_usd=100_000)
    )
    for f in flags:
        assert f.risk_inferred is not None
        assert f.risk_inferred["category"] == "compliance_us"
