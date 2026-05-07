"""Testes unitários — regras dormentes Onda 8 (W1-T02 · FP-001/2/3) + carry-trade (W1-T07 · FP-009)."""

from __future__ import annotations

import pytest

from pipeline.domain.services.suggestion_config import SuggestionGeneratorConfig
from pipeline.domain.services.suggestion_generator import SuggestionGenerator
from pipeline.domain.services.suggestion_rules import (
    ALL_RULES,
    CARRY_TRADE_MARGIN_PP,
    rule_endividamento_perigoso,
    rule_renda_passiva_real_baixa,
)
from pipeline.domain.types.suggestion import KIND_TO_CATEGORY, VALID_KINDS


@pytest.fixture
def gen() -> SuggestionGenerator:
    return SuggestionGenerator(SuggestionGeneratorConfig())


@pytest.fixture
def cfg() -> SuggestionGeneratorConfig:
    return SuggestionGeneratorConfig()


# =============================================================================
# FP-001 — rule_renda_passiva_real_baixa alias defensivo
# =============================================================================


class TestRendaPassivaAlias:
    def test_dispara_com_if_pct_alias(self, cfg):
        """Real snapshot expõe `if_pct` (não `progresso_if_pct`)."""
        snapshot = {
            "goals": {"if_pct": 55.0},
            "fluxo_caixa": {
                "renda_passiva_mensal_atual": 4_000.0,
                "despesa_mensal_media": 20_000.0,
            },
        }
        draft = rule_renda_passiva_real_baixa(snapshot, cfg)
        assert draft is not None
        assert draft.kind == "renda_passiva_real_baixa"
        assert draft.section_id == "S7"

    def test_dispara_com_progresso_if_pct_legado(self, cfg):
        """Backwards-compat: snapshot com `progresso_if_pct` ainda funciona."""
        snapshot = {
            "goals": {"progresso_if_pct": 55.0},
            "fluxo_caixa": {
                "renda_passiva_mensal_atual": 4_000.0,
                "despesa_mensal_media": 20_000.0,
            },
        }
        draft = rule_renda_passiva_real_baixa(snapshot, cfg)
        assert draft is not None

    def test_renda_passiva_alias_observada_brl(self, cfg):
        """Snapshot real expõe `goals.renda_passiva_mensal_observada_brl`."""
        snapshot = {
            "goals": {
                "if_pct": 55.0,
                "renda_passiva_mensal_observada_brl": 4_000.0,
            },
            "fluxo_caixa": {
                "despesa_mensal_media": 20_000.0,
                # Sem renda_passiva_mensal_atual — só observada_brl em goals.
            },
        }
        draft = rule_renda_passiva_real_baixa(snapshot, cfg)
        assert draft is not None

    def test_silencia_com_if_pct_baixo(self, cfg):
        snapshot = {
            "goals": {"if_pct": 30.0},
            "fluxo_caixa": {
                "renda_passiva_mensal_atual": 1_000.0,
                "despesa_mensal_media": 20_000.0,
            },
        }
        assert rule_renda_passiva_real_baixa(snapshot, cfg) is None

    def test_silencia_quando_nada_disponivel(self, cfg):
        assert rule_renda_passiva_real_baixa({}, cfg) is None


# =============================================================================
# FP-003 — rule_dolarizacao_atrasada removida
# =============================================================================


class TestDolarizacaoAtrasadaRemovida:
    def test_funcao_nao_existe(self):
        rule_names = {r.__name__ for r in ALL_RULES}
        assert "rule_dolarizacao_atrasada" not in rule_names

    def test_kind_nao_em_kind_to_category(self):
        assert "dolarizacao_atrasada" not in KIND_TO_CATEGORY

    def test_kind_nao_em_valid_kinds(self):
        assert "dolarizacao_atrasada" not in VALID_KINDS

    def test_snapshot_com_dolarizacao_silencia(self, gen):
        snapshot = {"dolarizacao": {"cobertura_pct": 0.0, "meta_pct": 50.0}}
        kinds = {d.kind for d in gen.generate(snapshot)}
        assert "dolarizacao_atrasada" not in kinds


# =============================================================================
# FP-009 — carry-trade endividamento
# =============================================================================


class TestCarryTradeEndividamento:
    def test_dispara_quando_custo_supera_retorno_mais_margem(self, cfg):
        """Cerbasi — dívida 25%a.a. + retorno 12%a.a. → carry-trade dispara."""
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 5.0,  # baixo (não dispara por %)
                "total_dividas": 30_000.0,
                "custo_medio_pct_aa": 25.0,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        draft = rule_endividamento_perigoso(snapshot, cfg)
        assert draft is not None
        assert draft.severity == "danger"
        assert draft.kind == "endividamento_perigoso"
        # Rationale menciona o conceito de carry-trade ou retorno esperado.
        assert "retorno esperado" in draft.rationale.lower()

    def test_silencia_quando_retorno_supera_custo(self, cfg):
        """Inverso: dívida 8%a.a. + retorno 12%a.a. → carry-trade NÃO dispara."""
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 5.0,
                "total_dividas": 30_000.0,
                "custo_medio_pct_aa": 8.0,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        assert rule_endividamento_perigoso(snapshot, cfg) is None

    def test_silencia_dentro_da_margem(self, cfg):
        """Custo dentro da margem (retorno + 1pp) não dispara."""
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 5.0,
                "total_dividas": 30_000.0,
                # 12.5 < 12 + 1 = 13.0 → dentro da margem, não dispara.
                "custo_medio_pct_aa": 12.5,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        assert rule_endividamento_perigoso(snapshot, cfg) is None

    def test_carry_margin_constant_documentada(self):
        """Constante nomeada com valor explícito (Cerbasi · Equilíbrio)."""
        assert CARRY_TRADE_MARGIN_PP == 1.0


# =============================================================================
# E2E (smoke) — todos os 4 cenários do prompt em sequência
# =============================================================================


class TestE2ECenariosFundamentais:
    """4 cenários cobertos: renda passiva alta, IF crescendo,
    dívida cara (carry-trade) e dívida barata (não dispara)."""

    def test_cenario_renda_passiva_alta_dispara(self, gen):
        snapshot = {
            "goals": {"if_pct": 55.0},
            "fluxo_caixa": {
                "renda_passiva_mensal_atual": 4_000.0,
                "despesa_mensal_media": 20_000.0,
            },
        }
        kinds = {d.kind for d in gen.generate(snapshot)}
        assert "renda_passiva_real_baixa" in kinds

    def test_cenario_if_crescendo_pontos_fortes_via_adapter(self):
        """Pontos fortes acessível via PontosFortesAnalyzer com goals.if_pct."""
        from pipeline.domain.services.pontos_fortes_analyzer import PontosFortesAnalyzer

        analyzer = PontosFortesAnalyzer()
        out = analyzer.analyze(
            score={"valor": 7.0, "classificacao": "Bom"},
            ratios={},
            patrimonio={},
            fluxo={},
            reserva={},
            goals={"if_pct": 25.0},
        )
        titulos = {p.titulo for p in out}
        assert "Caminho para Independência Financeira" in titulos

    def test_cenario_divida_cara_carry_trade(self, gen):
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 5.0,
                "total_dividas": 30_000.0,
                "custo_medio_pct_aa": 25.0,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        kinds = {d.kind for d in gen.generate(snapshot)}
        assert "endividamento_perigoso" in kinds

    def test_cenario_divida_barata_nao_dispara_por_carry(self, gen):
        snapshot = {
            "endividamento": {
                "percentual_patrimonio": 10.0,  # também baixo
                "total_dividas": 30_000.0,
                "custo_medio_pct_aa": 8.0,
            },
            "goals": {"retorno_esperado_pct_aa": 12.0},
        }
        kinds = {d.kind for d in gen.generate(snapshot)}
        assert "endividamento_perigoso" not in kinds
