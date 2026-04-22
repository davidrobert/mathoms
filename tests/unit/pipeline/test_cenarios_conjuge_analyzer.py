"""Tests — ``CenariosConjugeAnalyzer`` (Sessão A5c)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.cenarios_conjuge_analyzer import (  # noqa: E402
    CenarioItem,
    CenariosConjugeAnalyzer,
    CenariosConjugeConfig,
    CenariosConjugeResult,
)

_DAVID_DOB = date(1985, 6, 15)
_REF_DATE = date(2026, 4, 19)


def _cfg(**overrides) -> CenariosConjugeConfig:
    base = {
        "titular_dob": _DAVID_DOB,
        "retorno_real_anual_pct": 6.0,
        "aporte_base": 15_000,
        "fator_reduzido": 0.66,
        "cambio_usd_brl": 5.80,
        "renda_rn_minima_usd": 4000,
        "renda_rn_maxima_usd": 7000,
        "titular_key": "david",
        "conjuge_key": "mariana",
        "conjuge_nome": "Mariana",
        "reference_date": _REF_DATE,
    }
    base.update(overrides)
    return CenariosConjugeConfig(**base)


def _patrimonio(investivel: float = 500_000) -> dict:
    return {"investivel": investivel}


def _goals(if_meta: float = 5_000_000) -> dict:
    return {"if_meta": if_meta}


def _fluxo(salario_conjuge: float = 8_000) -> dict:
    """Fluxo com dataset CLT do cônjuge para extração da mediana."""
    return {
        "receita_despesa_mensal_detalhado": {
            "receita_datasets": [
                {
                    "label": "Receita CLT Mariana",
                    "data": [salario_conjuge] * 6 + [0] * 6,
                },
            ]
        }
    }


# =============================================================================
# Config
# =============================================================================


class TestConfig:
    def test_from_configs_extrai_defaults(self):
        cfg = CenariosConjugeConfig.from_configs(
            goals={
                "independencia_financeira": {"retorno_real_anual_pct": 7.0},
                "aportes": {"meta_aporte_mensal": 20_000},
                "simulacao": {"aporte_reduzido_fator": 0.5},
                "cenarios_conjuge": {
                    "renda_rn_minima_usd": 5000,
                    "renda_rn_maxima_usd": 8000,
                },
            },
            taxas={"cambio_usd_brl": 5.50},
            titular_dob=_DAVID_DOB,
        )
        assert cfg.retorno_real_anual_pct == 7.0
        assert cfg.aporte_base == 20_000
        assert cfg.fator_reduzido == 0.5
        assert cfg.cambio_usd_brl == 5.50
        assert cfg.renda_rn_minima_usd == 5000

    def test_from_configs_fallback_mariana_eua(self):
        cfg = CenariosConjugeConfig.from_configs(
            goals={"mariana_eua": {"renda_rn_minima_usd": 3500}},
            titular_dob=_DAVID_DOB,
        )
        assert cfg.renda_rn_minima_usd == 3500


# =============================================================================
# 3 Cenários
# =============================================================================


class TestCenarios:
    def test_retorna_tres_cenarios(self):
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        assert len(r.cenarios) == 3
        assert r.cenarios[0].nome == "Sem Trabalhar"
        assert r.cenarios[1].nome == "Com NCLEX"
        assert r.cenarios[2].nome == "Com NCLEX + Green Card"

    def test_s1_aporte_reduzido(self):
        cfg = _cfg(aporte_base=10_000, fator_reduzido=0.5)
        r = CenariosConjugeAnalyzer(cfg).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        # 50% de 10k = 5k.
        assert r.cenarios[0].aporte_mensal == 5_000

    def test_s2_aporte_maior_que_s1(self):
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        assert r.cenarios[1].aporte_mensal > r.cenarios[0].aporte_mensal

    def test_s3_aporte_maior_ou_igual_a_s2(self):
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        assert r.cenarios[2].aporte_mensal >= r.cenarios[1].aporte_mensal


class TestPrazo:
    def test_prazo_zero_quando_investivel_acima_meta(self):
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(investivel=6_000_000),
            goals=_goals(if_meta=5_000_000),
            fluxo=_fluxo(),
        )
        for c in r.cenarios:
            assert c.prazo_if_anos == 0.0

    def test_prazo_999_quando_zero_aporte_e_abaixo_meta(self):
        cfg = _cfg(aporte_base=0, fator_reduzido=0, retorno_real_anual_pct=0)
        r = CenariosConjugeAnalyzer(cfg).analyze(
            patrimonio=_patrimonio(investivel=0),
            goals=_goals(),
            fluxo=_fluxo(),
        )
        assert r.cenarios[0].prazo_if_anos == 999.0


class TestMedianaSalario:
    def test_calcula_mediana_dos_valores_nao_zero(self):
        fluxo = {
            "receita_despesa_mensal_detalhado": {
                "receita_datasets": [
                    {"label": "Receita CLT Mariana", "data": [5000, 5000, 10000, 0]},
                ]
            }
        }
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=fluxo
        )
        # Mediana de [5000, 5000, 10000] (ordenado) → posição 1 = 5000
        assert r.premissas["salario_mariana_clt_brl"] == 5000

    def test_zero_quando_sem_dataset_clt_do_conjuge(self):
        fluxo = {
            "receita_despesa_mensal_detalhado": {
                "receita_datasets": [
                    {"label": "Receita CLT David", "data": [10000]},
                ]
            }
        }
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=fluxo
        )
        assert r.premissas["salario_mariana_clt_brl"] == 0


class TestConversaoCambio:
    def test_renda_nclex_convertida(self):
        cfg = _cfg(cambio_usd_brl=5.00, renda_rn_minima_usd=4000)
        r = CenariosConjugeAnalyzer(cfg).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        # 4000 USD × 5.00 = 20_000 BRL
        assert r.premissas["renda_nclex_brl"] == 20_000
        assert r.premissas["renda_nclex_usd"] == 4000


class TestIdadesAnos:
    def test_ano_if_deriva_de_ref_date(self):
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        for c in r.cenarios:
            assert c.ano_if == 2026 + int(c.prazo_if_anos)

    def test_idade_titular_incrementa(self):
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        # David 40 em 2026-04-19.
        for c in r.cenarios:
            assert c.idade_titular == 40 + int(c.prazo_if_anos)


class TestResumos:
    def test_resumos_mencionam_conjuge_nome(self):
        r = CenariosConjugeAnalyzer(_cfg(conjuge_nome="Ana")).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        for c in r.cenarios:
            assert "Ana" in c.resumo or "renda" in c.resumo.lower()


class TestResult:
    def test_result_is_frozen_dataclass(self):
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        assert isinstance(r, CenariosConjugeResult)
        assert all(isinstance(c, CenarioItem) for c in r.cenarios)

    def test_legacy_dict_has_expected_fields(self):
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        d = r.to_legacy_dict()

        required = {"labels", "aportes", "prazos_if", "anos_if", "premissas", "cenarios"}
        assert required.issubset(d.keys())
        assert len(d["cenarios"]) == 3
        assert "idade_david_if" in d

    def test_premissas_completas(self):
        r = CenariosConjugeAnalyzer(_cfg()).analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo()
        )
        p = r.premissas

        for k in (
            "meta_if",
            "investivel_atual",
            "retorno_real_anual_pct",
            "cambio_usd_brl",
            "aporte_base",
            "fator_reduzido",
            "renda_nclex_usd",
            "renda_nclex_brl",
            "renda_gc_usd",
            "renda_gc_brl",
            "salario_mariana_clt_brl",
            "recovery_nclex_pct",
            "recovery_gc_pct",
        ):
            assert k in p
