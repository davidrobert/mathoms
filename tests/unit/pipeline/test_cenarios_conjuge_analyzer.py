"""Tests — `CenariosConjugeAnalyzer` + `should_render_conjuge_scenarios` (ADR-167)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.cenarios_conjuge_analyzer import (  # noqa: E402
    CenarioItem,
    CenariosConjugeAnalyzer,
    CenariosConjugeConfig,
    CenariosConjugeResult,
    should_render_conjuge_scenarios,
)

_TITULAR_DOB = date(1985, 6, 15)
_REF_DATE = date(2026, 4, 19)


def _cfg(**overrides) -> CenariosConjugeConfig:
    base = {
        "titular_dob": _TITULAR_DOB,
        "retorno_real_anual_pct": 6.0,
        "aporte_base": 15_000,
        "fator_reduzido": 0.66,
        "titular_key": "alice",
        "conjuge_key": "bob",
        "conjuge_nome": "Bob",
        "reference_date": _REF_DATE,
    }
    base.update(overrides)
    return CenariosConjugeConfig(**base)


def _patrimonio(investivel: float = 500_000) -> dict:
    return {"investivel_efetivo": investivel}


def _goals(if_meta: float = 5_000_000) -> dict:
    return {"if_meta": if_meta}


def _fluxo_salario_conjuge(valor: float = 8_000, label: str = "Receita CLT Bob") -> dict:
    return {
        "receita_despesa_mensal_detalhado": {
            "receita_datasets": [{"label": label, "data": [valor] * 6 + [0] * 6}]
        }
    }


# =============================================================================
# CenariosConjugeConfig.from_configs
# =============================================================================


class TestConfig:
    def test_from_configs_extrai_defaults(self):
        # ADR-177: ``fator_reduzido`` é rules-as-code, ignora simulacao.aporte_reduzido_fator do goals.
        cfg = CenariosConjugeConfig.from_configs(
            goals={
                "independencia_financeira": {"retorno_real_anual_pct": 7.0},
                "aportes": {"meta_aporte_mensal": 20_000},
                "simulacao": {"aporte_reduzido_fator": 0.5},  # ignorado pós-ADR-177
            },
            titular_dob=_TITULAR_DOB,
        )
        assert cfg.retorno_real_anual_pct == 7.0
        assert cfg.aporte_base == 20_000
        assert cfg.fator_reduzido == 0.66  # constante rules-as-code (ADR-177)

    def test_from_configs_aceita_goals_minimo(self):
        cfg = CenariosConjugeConfig.from_configs(
            goals={},
            titular_dob=_TITULAR_DOB,
            titular_key="alice",
            conjuge_key="bob",
            conjuge_nome="Bob",
        )
        assert cfg.aporte_base == 0.0
        assert cfg.fator_reduzido == 0.66  # default

    def test_config_sem_dependencia_de_usd(self):
        """ADR-167: cambio/USD removidos do contrato pós PR2."""
        cfg = CenariosConjugeConfig.from_configs(goals={}, titular_dob=_TITULAR_DOB)
        assert not hasattr(cfg, "cambio_usd_brl")
        assert not hasattr(cfg, "renda_rn_minima_usd")
        assert not hasattr(cfg, "renda_rn_maxima_usd")


# =============================================================================
# Analyzer — 1 cenário "Sem renda do cônjuge"
# =============================================================================


class TestAnalyzer:
    def test_um_unico_cenario(self):
        analyzer = CenariosConjugeAnalyzer(_cfg())
        result = analyzer.analyze(
            patrimonio=_patrimonio(),
            goals=_goals(),
            fluxo=_fluxo_salario_conjuge(),
        )
        assert isinstance(result, CenariosConjugeResult)
        assert len(result.cenarios) == 1

    def test_cenario_label_canonico(self):
        analyzer = CenariosConjugeAnalyzer(_cfg())
        result = analyzer.analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo_salario_conjuge()
        )
        assert result.cenarios[0].nome == "Sem renda do cônjuge"

    def test_aporte_eh_aporte_base_vezes_fator_reduzido(self):
        cfg = _cfg(aporte_base=10_000, fator_reduzido=0.6)
        analyzer = CenariosConjugeAnalyzer(cfg)
        result = analyzer.analyze(
            patrimonio=_patrimonio(),
            goals=_goals(),
            fluxo=_fluxo_salario_conjuge(),
        )
        assert result.cenarios[0].aporte_mensal == 6_000.0

    def test_premissas_universais_sem_nclex_gc(self):
        """ADR-167: premissas não exibem NCLEX/Green Card específicas."""
        analyzer = CenariosConjugeAnalyzer(_cfg())
        result = analyzer.analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo_salario_conjuge()
        )
        keys_proibidas = {
            "renda_nclex_usd",
            "renda_nclex_brl",
            "renda_gc_usd",
            "renda_gc_brl",
            "recovery_nclex_pct",
            "recovery_gc_pct",
            "cambio_usd_brl",
        }
        assert keys_proibidas.isdisjoint(set(result.premissas.keys()))

    def test_resumo_nao_menciona_nclex_green_card(self):
        analyzer = CenariosConjugeAnalyzer(_cfg())
        result = analyzer.analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo_salario_conjuge()
        )
        resumo = result.cenarios[0].resumo.lower()
        assert "nclex" not in resumo
        assert "green card" not in resumo
        assert "rn" not in resumo.split()

    def test_resumo_formato_monetario_brasileiro(self):
        """A37.l14 (PD-11): resumo exibia milhar US ("R$ 13,200/mês")."""
        cfg = _cfg(aporte_base=22_000, fator_reduzido=0.6)
        analyzer = CenariosConjugeAnalyzer(cfg)
        result = analyzer.analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo_salario_conjuge()
        )
        resumo = result.cenarios[0].resumo
        # 22_000 × 0.6 = 13_200 → "R$ 13,2k" (fmt_currency BR), nunca "R$ 13,200".
        assert "R$ 13,200" not in resumo
        assert "R$ 13,2k" in resumo

    def test_meta_atingida_retorna_prazo_zero(self):
        analyzer = CenariosConjugeAnalyzer(_cfg())
        result = analyzer.analyze(
            patrimonio=_patrimonio(investivel=10_000_000),
            goals=_goals(if_meta=5_000_000),
            fluxo=_fluxo_salario_conjuge(),
        )
        assert result.cenarios[0].prazo_if_anos == 0.0

    def test_aporte_zero_resulta_em_ausencia_explicita(self):
        """Sem prazo projetável nada dele deriva — era 999 → ano 3025, idade 1040."""
        cfg = _cfg(aporte_base=0)
        analyzer = CenariosConjugeAnalyzer(cfg)
        result = analyzer.analyze(
            patrimonio=_patrimonio(),
            goals=_goals(),
            fluxo=_fluxo_salario_conjuge(),
        )
        cenario = result.cenarios[0]
        assert cenario.prazo_if_anos is None
        assert cenario.ano_if is None
        assert cenario.idade_titular is None
        assert "não projetável" in cenario.resumo
        assert "999" not in cenario.resumo

    def test_to_legacy_dict_shape(self):
        analyzer = CenariosConjugeAnalyzer(_cfg())
        result = analyzer.analyze(
            patrimonio=_patrimonio(), goals=_goals(), fluxo=_fluxo_salario_conjuge()
        )
        d = result.to_legacy_dict()
        assert d["labels"] == ["Sem renda do cônjuge"]
        assert len(d["aportes"]) == 1
        assert len(d["prazos_if"]) == 1
        assert len(d["anos_if"]) == 1
        assert "premissas" in d
        assert isinstance(d["cenarios"], list)


# =============================================================================
# Eligibility gate (ADR-167) — 4 casos canônicos
# =============================================================================


class TestEligibilityGate:
    """ADR-167: should_render_conjuge_scenarios — 4 casos canônicos."""

    def _family_casal(self) -> dict:
        return {
            "titular": "alice",
            "membros": {
                "alice": {"papel": "titular", "nome_curto": "Alice"},
                "bob": {"papel": "conjuge", "nome_curto": "Bob"},
            },
        }

    def _family_solteiro(self) -> dict:
        return {
            "titular": "alice",
            "membros": {"alice": {"papel": "titular", "nome_curto": "Alice"}},
        }

    def _fluxo_2_rendas(self, *, titular: float, conjuge: float) -> dict:
        return {
            "receita_despesa_mensal_detalhado": {
                "receita_datasets": [
                    {"label": "Receita CLT Alice", "data": [titular] * 6 + [0] * 6},
                    {"label": "Receita CLT Bob", "data": [conjuge] * 6 + [0] * 6},
                ]
            }
        }

    def test_solteiro_sem_o_que_stressar(self):
        assert (
            should_render_conjuge_scenarios(
                family_members=self._family_solteiro(),
                fluxo={},
                goals=_goals(),
            )
            is False
        )

    def test_casal_sem_meta_if(self):
        assert (
            should_render_conjuge_scenarios(
                family_members=self._family_casal(),
                fluxo=self._fluxo_2_rendas(titular=10_000, conjuge=5_000),
                goals={"if_meta": 0},
            )
            is False
        )

    def test_casal_955_renda_conjuge_abaixo_de_15pct(self):
        # Cônjuge ~5% da renda familiar — abaixo do threshold 15%, vira ruído
        assert (
            should_render_conjuge_scenarios(
                family_members=self._family_casal(),
                fluxo=self._fluxo_2_rendas(titular=20_000, conjuge=1_000),
                goals=_goals(),
            )
            is False
        )

    def test_casal_70_30_meta_if_eligivel(self):
        # Cônjuge ~30% da renda familiar — caso canônico de elegibilidade
        assert (
            should_render_conjuge_scenarios(
                family_members=self._family_casal(),
                fluxo=self._fluxo_2_rendas(titular=14_000, conjuge=6_000),
                goals=_goals(),
            )
            is True
        )

    def test_casal_sem_renda_do_conjuge(self):
        assert (
            should_render_conjuge_scenarios(
                family_members=self._family_casal(),
                fluxo=self._fluxo_2_rendas(titular=15_000, conjuge=0),
                goals=_goals(),
            )
            is False
        )
