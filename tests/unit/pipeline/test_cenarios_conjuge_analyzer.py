"""Tests — `CenariosConjugeAnalyzer` + `veredito_cenario_conjuge` (ADR-167)."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.cenarios_conjuge_analyzer import (  # noqa: E402
    CenarioItem,
    CenariosConjugeAnalyzer,
    CenariosConjugeConfig,
    CenariosConjugeResult,
    VereditoCenarioConjuge,
    veredito_cenario_conjuge,
)
from pipeline.domain.services.narrativas.format_helpers import (  # noqa: E402
    CENARIO_CONJUGE_META_ATINGIDA,
    CENARIO_CONJUGE_SEM_APORTE,
)

_TITULAR_DOB = date(1985, 6, 15)
_REF_DATE = date(2026, 4, 19)


def _cfg(**overrides) -> CenariosConjugeConfig:
    base = {
        "titular_dob": _TITULAR_DOB,
        "retorno_real_anual_pct": 6.0,
        "aporte_base": Decimal("15000"),
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
        assert cfg.aporte_base is None  # ausência, não zero (ADR-373)
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
        cfg = _cfg(aporte_base=Decimal("10000"), fator_reduzido=0.6)
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
        cfg = _cfg(aporte_base=Decimal("22000"), fator_reduzido=0.6)
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

    def test_aporte_ausente_resulta_em_ausencia_explicita(self):
        """Sem prazo projetável nada dele deriva — era 999 → ano 3025, idade 1040."""
        cfg = _cfg(aporte_base=None)
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
        assert "999" not in cenario.resumo

    @pytest.mark.parametrize("aporte", [Decimal("0"), 15_000.0])
    def test_config_recusa_zero_e_float(self, aporte):
        """Zero não é declarável (ADR-373) e dinheiro não é float (ADR-090)."""
        with pytest.raises(ValueError, match="aporte_base"):
            _cfg(aporte_base=aporte)

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
# Aporte não declarado — zero no lugar de ausente (COPY_GUIDELINES §4.3)
# =============================================================================

# Zero não é declarável (`goal.aporte_mensal.schema.json`: `exclusiveMinimum: 0`,
# ADR-373), então as três formas chegam ao analyzer como a mesma ausência.
_SEM_APORTE_DECLARADO = [{}, {"meta_aporte_mensal": None}, {"meta_aporte_mensal": 0}]


def _analisa_sem_aporte(aportes: dict, investivel: float = 500_000) -> CenariosConjugeResult:
    cfg = CenariosConjugeConfig.from_configs(
        goals={"aportes": aportes},
        titular_dob=_TITULAR_DOB,
        conjuge_nome="Bob",
        reference_date=_REF_DATE,
    )
    return CenariosConjugeAnalyzer(cfg).analyze(
        patrimonio=_patrimonio(investivel), goals=_goals(), fluxo=_fluxo_salario_conjuge()
    )


class TestAporteNaoDeclarado:
    @pytest.mark.parametrize("aportes", _SEM_APORTE_DECLARADO)
    def test_resumo_nao_afirma_aporte_zero(self, aportes):
        resumo = _analisa_sem_aporte(aportes).cenarios[0].resumo
        assert "R$ 0" not in resumo
        assert "N/D" not in resumo
        assert "66%" not in resumo
        # ADR-373 D2: a redação nomeava a nossa incapacidade, não o insumo que falta.
        assert "não projetável" not in resumo
        assert resumo == CENARIO_CONJUGE_SEM_APORTE

    def test_meta_atingida_sem_aporte_mantem_prazo_zero(self):
        """Meta atingida independe do aporte: o solver devolve 0 antes de olhá-lo."""
        cenario = _analisa_sem_aporte({}, investivel=10_000_000).cenarios[0]
        assert cenario.prazo_if_anos == 0.0
        # A frase de ausência seria falsa aqui: a perda da renda não adia o que já chegou.
        assert cenario.resumo == CENARIO_CONJUGE_META_ATINGIDA

    @pytest.mark.parametrize("aportes", _SEM_APORTE_DECLARADO)
    def test_payload_publica_ausencia_e_nao_zero(self, aportes):
        d = _analisa_sem_aporte(aportes).to_legacy_dict()
        assert d["aportes"] == [None]
        assert d["cenarios"][0]["aporte_mensal"] is None
        assert d["premissas"]["aporte_base"] is None
        assert d["prazos_if"] == [None]
        assert d["anos_if"] == [None]


# =============================================================================
# Elegibilidade (ADR-167 §Emenda 2026-10-09)
# =============================================================================


# Os casos 95/5 e "1 renda" do gate original saíram: o produtor real do label de
# receita não carrega o nome do membro, então a divisão não é mensurável — a
# retomada está na emenda da ADR-167.
class TestVereditoElegibilidade:
    """Só fatos de cadastro e de meta decidem; a divisão de renda não tem sinal."""

    def test_solteiro_nao_e_elegivel(self):
        veredito = veredito_cenario_conjuge(conjuge_key="", if_meta=5_000_000)
        assert veredito is VereditoCenarioConjuge.sem_conjuge_cadastrado

    def test_casal_sem_meta_if_nao_e_elegivel(self):
        veredito = veredito_cenario_conjuge(conjuge_key="bob", if_meta=0)
        assert veredito is VereditoCenarioConjuge.sem_meta_if

    def test_casal_com_meta_if_e_elegivel(self):
        veredito = veredito_cenario_conjuge(conjuge_key="bob", if_meta=5_000_000)
        assert veredito is VereditoCenarioConjuge.elegivel

    def test_sem_conjuge_prevalece_sobre_sem_meta(self):
        # O motivo logado é o estrutural: sem cônjuge, a meta nunca o tornaria elegível.
        veredito = veredito_cenario_conjuge(conjuge_key="", if_meta=0)
        assert veredito is VereditoCenarioConjuge.sem_conjuge_cadastrado
