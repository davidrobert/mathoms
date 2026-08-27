"""Tests — ``IFProjector`` (Sessão A5a · Fase 8)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.if_projector import (  # noqa: E402
    MOTIVO_SEM_TRAJETORIA,
    BaseDaMetaIF,
    IFProjection,
    IFProjector,
    IFProjectorConfig,
    compor_meta_if,
    extract_if_meta_from_text,
    extract_if_trs_from_text,
    extract_renda_passiva_from_text,
)

_REF_DATE = date(2026, 4, 19)
_DAVID_DOB = date(1985, 6, 15)
_MARIANA_DOB = date(1987, 3, 20)


def _config(**overrides) -> IFProjectorConfig:
    base = {
        "if_meta": 5_000_000.0,
        "if_trs_pct": 4.0,
        "titular_dob": _DAVID_DOB,
        "aporte_mensal": 10_000.0,
        "retorno_real_anual_pct": 6.0,
        "taxa_retirada_segura_pct": 4.0,
        "reference_date": _REF_DATE,
        "titular_key": "david",
        "conjuge_key": "",
        "conjuge_dob": None,
    }
    base.update(overrides)
    return IFProjectorConfig(**base)


# =============================================================================
# Config — from_configs
# =============================================================================


class TestConfigFromConfigs:
    def test_builds_from_goals_dict(self):
        goals = {
            "independencia_financeira": {
                "if_meta": 5_000_000,
                "trs_pct": 4.0,
                "taxa_retirada_segura_pct": 4.5,
                "retorno_real_anual_pct": 7.0,
            },
            "aportes": {"meta_aporte_mensal": 12_000},
        }
        cfg = IFProjectorConfig.from_configs(
            goals=goals,
            titular_dob=_DAVID_DOB,
            reference_date=_REF_DATE,
        )

        assert cfg.if_meta == 5_000_000.0
        assert cfg.if_trs_pct == 4.0
        assert cfg.taxa_retirada_segura_pct == 4.5
        assert cfg.retorno_real_anual_pct == 7.0
        assert cfg.aporte_mensal == 12_000.0

    def test_raises_when_if_meta_missing(self):
        goals = {"independencia_financeira": {"trs_pct": 4.0}}
        with pytest.raises(ValueError, match="IF meta"):
            IFProjectorConfig.from_configs(goals=goals, titular_dob=_DAVID_DOB)

    def test_raises_when_trs_missing(self):
        goals = {"independencia_financeira": {"if_meta": 5_000_000}}
        with pytest.raises(ValueError, match="TRS"):
            IFProjectorConfig.from_configs(goals=goals, titular_dob=_DAVID_DOB)

    def test_defaults_when_optional_absent(self):
        goals = {"independencia_financeira": {"if_meta": 1_000_000, "trs_pct": 4.0}}
        cfg = IFProjectorConfig.from_configs(goals=goals, titular_dob=_DAVID_DOB)

        assert cfg.taxa_retirada_segura_pct == 4.0
        assert cfg.retorno_real_anual_pct == 6.0
        assert cfg.aporte_mensal == 0.0


# =============================================================================
# Extractors (life_plan_goals.md regex)
# =============================================================================


class TestExtractors:
    def test_extract_if_meta_brazilian_format(self):
        content = "Meta IF: **R$ 5.000.000** até 2045"
        assert extract_if_meta_from_text(content) == 5_000_000.0

    def test_extract_if_meta_none_when_absent(self):
        assert extract_if_meta_from_text("texto sem meta") is None

    def test_extract_if_trs_with_comma(self):
        assert extract_if_trs_from_text("TRS conservador: 3,5%") == 3.5

    def test_extract_if_trs_none_when_absent(self):
        assert extract_if_trs_from_text("sem trs aqui") is None

    def test_extract_renda_passiva_atual(self):
        content = "Renda passiva atual: R$ 2.500,00 mensal"
        assert extract_renda_passiva_from_text(content) == 2_500.0

    def test_extract_renda_passiva_zero_when_absent(self):
        assert extract_renda_passiva_from_text("outros dados") == 0.0


# =============================================================================
# Project — casos principais
# =============================================================================


class TestProject:
    def test_if_pct_when_below_target(self):
        p = IFProjector(_config()).project(investivel=500_000)

        assert p.if_pct == pytest.approx(10.0)  # 500k / 5M
        assert p.if_gap == pytest.approx(4_500_000.0)

    def test_if_already_reached_returns_zero_prazo(self):
        p = IFProjector(_config()).project(investivel=5_500_000)

        assert p.prazo_anos_realista == 0.0
        assert p.idade_titular_if == 40  # DOB 1985-06-15, ref 2026-04-19 → 40

    def test_prazo_compound_interest_math(self):
        # Cenário conhecido: 1M de investivel, aporte 10k/mes, 6% real anual,
        # meta 5M. Resolvendo: n_meses ≈ log((5M + PMT/r)/(1M + PMT/r)) / log(1+r)
        p = IFProjector(_config()).project(investivel=1_000_000)

        # ~13-14 anos (validação grosseira; exatidão depende da math).
        assert 10 < p.prazo_anos_realista < 20

    def test_prazo_ausente_when_zero_aporte_and_below_target(self):
        """Sem prazo projetável, tudo que dele deriva é ausência — não 999/1040."""
        cfg = _config(aporte_mensal=0, retorno_real_anual_pct=0)
        p = IFProjector(cfg).project(investivel=100_000)

        assert p.prazo_anos_realista is None
        assert p.idade_titular_if is None
        assert p.ano_if is None
        # aporte 0 E retorno 0: é o caso SEM TRAJETÓRIA, o único que pode
        # afirmar inviabilidade (ADR-373).
        assert p.motivo_prazo_indefinido == MOTIVO_SEM_TRAJETORIA

    def test_idade_titular_increments_with_anos_restantes(self):
        p = IFProjector(_config()).project(investivel=1_000_000)

        years = int(p.prazo_anos_realista)
        # 40 anos em 2026 + prazo
        assert p.idade_titular_if == 40 + years

    def test_conjuge_age_present_when_dob_given(self):
        cfg = _config(conjuge_dob=_MARIANA_DOB, conjuge_key="mariana")
        p = IFProjector(cfg).project(investivel=1_000_000)

        years = int(p.prazo_anos_realista)
        # Mariana nasceu em 1987-03-20 — em 2026-04-19 ela tem 39.
        assert p.idade_conjuge_if == 39 + years

    def test_conjuge_age_none_when_no_dob(self):
        p = IFProjector(_config()).project(investivel=1_000_000)

        assert p.idade_conjuge_if is None

    def test_ano_if(self):
        p = IFProjector(_config()).project(investivel=1_000_000)

        assert p.ano_if == 2026 + int(p.prazo_anos_realista)

    def test_renda_passiva_estimada_4pct(self):
        cfg = _config(taxa_retirada_segura_pct=4.0)
        p = IFProjector(cfg).project(investivel=1_200_000)

        # 1.2M × 4% / 12 = 4000/mes
        assert p.renda_passiva_estimada_4pct == pytest.approx(4_000.0)

    def test_if_trs_monthly_value(self):
        cfg = _config(if_meta=5_000_000, if_trs_pct=4.0)
        p = IFProjector(cfg).project(investivel=100_000)

        # 5M × (4% / 12) = 16_666.67
        assert p.if_trs_monthly_value == pytest.approx(16_666.67, rel=1e-3)


# =============================================================================
# to_legacy_dict
# =============================================================================


class TestLegacyDict:
    def test_produces_expected_fields(self):
        p = IFProjector(_config()).project(investivel=500_000)

        d = p.to_legacy_dict()

        required = {
            "if_meta",
            "if_meta_bruta",
            "if_meta_base",
            "if_trs",
            "if_trs_monthly_value",
            "if_pct",
            "if_gap",
            "prazo_anos_realista",
            "idade_titular_if",
            "ano_if",
            "renda_passiva_estimada_4pct",
        }
        assert required.issubset(d.keys())

    def test_conjuge_field_when_present(self):
        cfg = _config(conjuge_dob=_MARIANA_DOB, conjuge_key="mariana")
        p = IFProjector(cfg).project(investivel=500_000)

        d = p.to_legacy_dict()

        assert "idade_conjuge_if" in d

    def test_conjuge_field_absent_when_no_conjuge(self):
        p = IFProjector(_config()).project(investivel=500_000)

        d = p.to_legacy_dict()

        # ADR-338: contrato role-keyed — idade_titular_if sempre presente;
        # idade_conjuge_if só aparece quando há cônjuge.
        assert "idade_titular_if" in d
        assert "idade_conjuge_if" not in d


# =============================================================================
# Base da meta — [[ADR-418]] / A40.l91 (PV9-16)
# =============================================================================


class TestBaseDaMetaIF:
    """O invariante é o par numerador↔meta, não a fórmula ([[ADR-418]] §D1)."""

    def test_sem_renda_externa_a_meta_e_a_bruta(self):
        p = IFProjector(_config(if_meta=5_000_000, if_trs_pct=4.0)).project(investivel=1_000_000)

        assert p.if_meta == p.if_meta_bruta == 5_000_000
        assert p.if_meta_base is BaseDaMetaIF.renda_alvo_bruta
        assert p.renda_passiva_fora_do_investivel_mensal is None
        assert "renda_passiva_fora_do_investivel_mensal_brl" not in p.to_legacy_dict()

    def test_termo_medido_em_zero_e_publicado(self):
        """`0.0` é medida ("nada fora"); `None` é ausência de medida ([[ADR-418]] §D3)."""
        p = IFProjector(_config()).project(
            investivel=1_000_000, renda_passiva_fora_do_investivel_mensal=0.0
        )

        assert p.to_legacy_dict()["renda_passiva_fora_do_investivel_mensal_brl"] == 0.0
        assert p.if_meta_base is BaseDaMetaIF.renda_alvo_bruta

    def test_renda_externa_desconta_a_meta_capitalizada(self):
        # 10k/mês a 4% de retirada = 10k × 12 / 0,04 = 3M a menos de patrimônio.
        p = IFProjector(_config(if_meta=5_000_000, if_trs_pct=4.0)).project(
            investivel=1_000_000, renda_passiva_fora_do_investivel_mensal=10_000.0
        )

        assert p.if_meta == pytest.approx(2_000_000.0)
        assert p.if_meta_bruta == 5_000_000
        assert p.if_meta_base is BaseDaMetaIF.renda_alvo_liquida_de_renda_externa

    def test_identidade_da_composicao_fecha_ao_centavo(self):
        """`if_meta == if_meta_bruta − termo × 12 ÷ TRS` — o que o CV5 afirma."""
        p = IFProjector(_config(if_meta=5_000_000, if_trs_pct=5.0)).project(
            investivel=1_000_000, renda_passiva_fora_do_investivel_mensal=3_333.33
        )

        esperado = p.if_meta_bruta - (p.renda_passiva_fora_do_investivel_mensal or 0) * 12 / 0.05
        assert abs(p.if_meta - esperado) < 0.01

    def test_gap_e_progresso_leem_a_mesma_base(self):
        """A identidade `gap = meta − investível` fecha ao centavo (§Critério A40.l91)."""
        p = IFProjector(_config(if_meta=5_000_000, if_trs_pct=4.0)).project(
            investivel=1_000_000, renda_passiva_fora_do_investivel_mensal=5_000.0
        )

        assert abs(p.if_gap - (p.if_meta - 1_000_000)) < 0.01
        assert p.if_pct == pytest.approx(1_000_000 / p.if_meta * 100)

    def test_mutacao_renda_externa_move_o_progresso_para_cima(self):
        """Prova por mutação (§Critério A40.l91): mais renda externa ⇒ mais progresso."""
        cfg = _config(if_meta=5_000_000, if_trs_pct=4.0)
        antes = IFProjector(cfg).project(investivel=1_000_000)
        depois = IFProjector(cfg).project(
            investivel=1_000_000, renda_passiva_fora_do_investivel_mensal=4_000.0
        )

        assert depois.if_pct > antes.if_pct
        assert depois.if_gap < antes.if_gap
        assert depois.if_meta < antes.if_meta

    def test_renda_alvo_declarada_nao_se_move_com_o_desconto(self):
        """`if_trs_monthly_value` é o alvo DECLARADO — sai da bruta, sempre ([[ADR-418]] §D3)."""
        cfg = _config(if_meta=5_000_000, if_trs_pct=4.0)
        antes = IFProjector(cfg).project(investivel=1_000_000)
        depois = IFProjector(cfg).project(
            investivel=1_000_000, renda_passiva_fora_do_investivel_mensal=4_000.0
        )

        assert depois.if_trs_monthly_value == antes.if_trs_monthly_value

    def test_meta_nunca_fica_negativa(self):
        """Renda externa acima do alvo zera a meta em vez de virar número inexistente."""
        p = IFProjector(_config(if_meta=1_000_000, if_trs_pct=4.0)).project(
            investivel=500_000, renda_passiva_fora_do_investivel_mensal=99_000.0
        )

        assert p.if_meta == 0.0
        assert p.if_gap == 0.0
        assert p.prazo_anos_realista == 0.0
        # 0% aqui contradiria o gap e o prazo, que já dizem "chegou".
        assert p.if_pct == 100.0

    def test_trs_ausente_nao_capitaliza_o_desconto(self):
        """TRS zero não pode virar divisão por zero nem descontar às cegas."""
        assert (
            compor_meta_if(
                meta_bruta=1_000_000.0,
                renda_passiva_fora_do_investivel_mensal=5_000.0,
                if_trs_pct=0.0,
            )
            == 1_000_000.0
        )

    def test_termo_nao_medido_nao_desconta(self):
        """`None` não pode virar zero silencioso nem desconto às cegas."""
        assert (
            compor_meta_if(
                meta_bruta=1_000_000.0,
                renda_passiva_fora_do_investivel_mensal=None,
                if_trs_pct=4.0,
            )
            == 1_000_000.0
        )
