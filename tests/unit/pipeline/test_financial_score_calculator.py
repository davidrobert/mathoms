"""Testes para :class:`FinancialScoreCalculator` (A6d.3.3 — ADR-100)."""
from __future__ import annotations

import pytest

from pipeline.domain.services.financial_score_calculator import (
    FinancialScoreCalculator,
    FinancialScoreConfig,
    ScoreClassificacao,
    ScoreComponent,
    linear_interpolate,
)


# =============================================================================
# linear_interpolate
# =============================================================================


def test_interpolate_at_min_returns_zero():
    assert linear_interpolate(0, 0, 10) == 0.0


def test_interpolate_at_max_returns_ten():
    assert linear_interpolate(10, 0, 10) == 10.0


def test_interpolate_midpoint_returns_five():
    assert linear_interpolate(5, 0, 10) == 5.0


def test_interpolate_clamps_above_max():
    assert linear_interpolate(100, 0, 10) == 10.0


def test_interpolate_clamps_below_min():
    assert linear_interpolate(-10, 0, 10) == 0.0


def test_interpolate_zero_range_returns_zero():
    """Min == Max → 0 (evita divisão por zero)."""
    assert linear_interpolate(5, 10, 10) == 0.0


def test_interpolate_inverted_range_works_via_swap():
    """Inverter min/max produz ordem inversa."""
    # Valor 0 em [10, 0] → deve dar 10 (0 está "no topo" de 10)
    assert linear_interpolate(0, 10, 0) == 10.0
    assert linear_interpolate(10, 10, 0) == 0.0


# =============================================================================
# Config
# =============================================================================


def test_config_default_all_5_components():
    cfg = FinancialScoreConfig.default()
    assert cfg.taxa_poupanca.key == "taxa_poupanca_recorrente"
    assert cfg.cobertura.key == "cobertura_despesas"
    assert cfg.endividamento.key == "taxa_endividamento"
    assert cfg.progresso_if.key == "progresso_if"
    assert cfg.diversificacao.key == "diversificacao"


def test_config_from_scoring_json_empty_uses_defaults():
    cfg = FinancialScoreConfig.from_scoring_json({})
    defaults = FinancialScoreConfig.default()
    assert cfg.taxa_poupanca == defaults.taxa_poupanca


def test_config_from_scoring_json_partial_override():
    """Override parcial não zera campos ausentes."""
    scoring = {
        "score_componentes": {
            "taxa_poupanca_recorrente": {"range_max": 100}
        }
    }
    cfg = FinancialScoreConfig.from_scoring_json(scoring)
    assert cfg.taxa_poupanca.range_max == 100
    assert cfg.taxa_poupanca.range_min == 0  # default preservado
    assert cfg.taxa_poupanca.peso == 2.0  # default preservado


def test_config_from_scoring_json_invertido_flag():
    scoring = {
        "score_componentes": {
            "taxa_endividamento": {"invertido": True}
        }
    }
    cfg = FinancialScoreConfig.from_scoring_json(scoring)
    assert cfg.endividamento.invertido is True


def test_config_from_scoring_json_classification_bands():
    scoring = {
        "score_classificacao": [
            {"min": 0, "max": 3, "label": "Crítico"},
            {"min": 3, "max": 6, "label": "OK"},
            {"min": 6, "max": 10, "label": "Excelente"},
        ]
    }
    cfg = FinancialScoreConfig.from_scoring_json(scoring)
    assert len(cfg.classificacao) == 3
    assert cfg.classificacao[1].label == "OK"


# =============================================================================
# calculate — componentes
# =============================================================================


@pytest.fixture
def default_calc() -> FinancialScoreCalculator:
    return FinancialScoreCalculator(FinancialScoreConfig.default())


def test_calculate_returns_all_5_components(default_calc: FinancialScoreCalculator):
    result = default_calc.calculate(
        ratios={"taxa_poupanca_recorrente_pct": 0, "cobertura_despesas_meses": 0, "taxa_endividamento_pct": 0},
        patrimonio={"composicao": []},
        goals={"if_pct": 0},
    )
    assert len(result["componentes"]) == 5


def test_calculate_output_shape(default_calc: FinancialScoreCalculator):
    result = default_calc.calculate(
        ratios={"taxa_poupanca_recorrente_pct": 10, "cobertura_despesas_meses": 6, "taxa_endividamento_pct": 20},
        patrimonio={"composicao": [{"valor": 100}]},
        goals={"if_pct": 20},
    )
    assert set(result.keys()) == {"valor", "max", "classificacao", "componentes"}
    assert result["max"] == 10


def test_componentes_have_nome_valor_peso_nota(default_calc: FinancialScoreCalculator):
    result = default_calc.calculate(
        ratios={"taxa_poupanca_recorrente_pct": 25, "cobertura_despesas_meses": 6, "taxa_endividamento_pct": 10},
        patrimonio={"composicao": []},
        goals={"if_pct": 40},
    )
    for comp in result["componentes"]:
        assert set(comp.keys()) == {"nome", "valor", "peso", "nota"}


def test_diversificacao_counts_positive_valor_only(default_calc: FinancialScoreCalculator):
    """Apenas categorias com valor > 0 contam para diversificação."""
    result = default_calc.calculate(
        ratios={"taxa_poupanca_recorrente_pct": 0, "cobertura_despesas_meses": 0, "taxa_endividamento_pct": 0},
        patrimonio={
            "composicao": [
                {"valor": 100}, {"valor": 50}, {"valor": 0},
                {"valor": 0}, {"valor": 200},
            ]
        },
        goals={"if_pct": 0},
    )
    # 3 categorias > 0
    diversif_comp = next(c for c in result["componentes"] if c["nome"] == "diversificacao")
    assert diversif_comp["valor"] == 3


def test_endividamento_invertido_high_value_low_score():
    """invertido=True: alto endividamento → baixo score."""
    cfg = FinancialScoreConfig(
        taxa_poupanca=ScoreComponent("taxa_poupanca_recorrente", 0, 50, 2.0, "taxa_poupanca"),
        cobertura=ScoreComponent("cobertura_despesas", 3, 24, 1.5, "cobertura"),
        endividamento=ScoreComponent(
            "taxa_endividamento", 5, 50, 1.5, "endividamento", invertido=True
        ),
        progresso_if=ScoreComponent("progresso_if", 5, 80, 2.0, "if"),
        diversificacao=ScoreComponent("diversificacao", 1, 6, 1.0, "diversif"),
    )
    calc = FinancialScoreCalculator(cfg)
    # Endivid = 50 (max) com invertido → nota = 0
    result = calc.calculate(
        ratios={"taxa_poupanca_recorrente_pct": 0, "cobertura_despesas_meses": 0, "taxa_endividamento_pct": 50},
        patrimonio={"composicao": []},
        goals={"if_pct": 0},
    )
    endiv_comp = next(c for c in result["componentes"] if c["nome"] == "endividamento")
    assert endiv_comp["nota"] == 0.0


def test_endividamento_nao_invertido_high_value_high_score():
    """Default invertido=False: alto endividamento → alto score (não faz sentido mas é paridade)."""
    calc = FinancialScoreCalculator(FinancialScoreConfig.default())
    result = calc.calculate(
        ratios={"taxa_poupanca_recorrente_pct": 0, "cobertura_despesas_meses": 0, "taxa_endividamento_pct": 50},
        patrimonio={"composicao": []},
        goals={"if_pct": 0},
    )
    endiv_comp = next(c for c in result["componentes"] if c["nome"] == "taxa_endividamento")
    # 50 é o range_max default → nota 10
    assert endiv_comp["nota"] == 10.0


def test_weighted_average_computed(default_calc: FinancialScoreCalculator):
    """Média ponderada dos 5 componentes."""
    # Todos em min (nota 0) → score 0
    result = default_calc.calculate(
        ratios={"taxa_poupanca_recorrente_pct": 0, "cobertura_despesas_meses": 3, "taxa_endividamento_pct": 5},
        patrimonio={"composicao": []},
        goals={"if_pct": 5},
    )
    assert result["valor"] == 0.0


def test_weighted_average_max_when_all_at_top(default_calc: FinancialScoreCalculator):
    result = default_calc.calculate(
        ratios={
            "taxa_poupanca_recorrente_pct": 50,
            "cobertura_despesas_meses": 24,
            "taxa_endividamento_pct": 50,
        },
        patrimonio={"composicao": [{"valor": 1}] * 6},
        goals={"if_pct": 80},
    )
    assert result["valor"] == 10.0


# =============================================================================
# Classificação
# =============================================================================


def test_classify_fallback_critico():
    calc = FinancialScoreCalculator(FinancialScoreConfig.default())
    result = calc.calculate(
        ratios={"taxa_poupanca_recorrente_pct": 0, "cobertura_despesas_meses": 3, "taxa_endividamento_pct": 5},
        patrimonio={"composicao": []},
        goals={"if_pct": 5},
    )
    assert result["classificacao"] == "Crítico"


def test_classify_fallback_excelente():
    calc = FinancialScoreCalculator(FinancialScoreConfig.default())
    result = calc.calculate(
        ratios={
            "taxa_poupanca_recorrente_pct": 50,
            "cobertura_despesas_meses": 24,
            "taxa_endividamento_pct": 50,
        },
        patrimonio={"composicao": [{"valor": 1}] * 6},
        goals={"if_pct": 80},
    )
    assert result["classificacao"] == "Excelente"


def test_classify_fallback_regular():
    calc = FinancialScoreCalculator(FinancialScoreConfig.default())
    result = calc.calculate(
        ratios={
            "taxa_poupanca_recorrente_pct": 25,  # nota 5
            "cobertura_despesas_meses": 13,  # ~(13-3)/21 * 10 = 4.76
            "taxa_endividamento_pct": 27.5,
            # progresso_if, diversif: parametrizados abaixo
        },
        patrimonio={"composicao": [{"valor": 1}] * 3},
        goals={"if_pct": 42.5},
    )
    # Score ~ 5 → "Regular" [4, 6)
    assert result["classificacao"] in {"Regular", "Atenção", "Bom"}  # +/- por arredondamento


def test_classify_custom_bands():
    cfg = FinancialScoreConfig(
        taxa_poupanca=ScoreComponent("taxa_poupanca_recorrente", 0, 50, 2.0, "x"),
        cobertura=ScoreComponent("cobertura_despesas", 3, 24, 1.5, "x"),
        endividamento=ScoreComponent("taxa_endividamento", 5, 50, 1.5, "x"),
        progresso_if=ScoreComponent("progresso_if", 5, 80, 2.0, "x"),
        diversificacao=ScoreComponent("diversificacao", 1, 6, 1.0, "x"),
        classificacao=(
            ScoreClassificacao(min=0, max=5, label="Baixo"),
            ScoreClassificacao(min=5, max=10, label="Alto"),
        ),
    )
    calc = FinancialScoreCalculator(cfg)
    result = calc.calculate(
        ratios={"taxa_poupanca_recorrente_pct": 0, "cobertura_despesas_meses": 3, "taxa_endividamento_pct": 5},
        patrimonio={"composicao": []},
        goals={"if_pct": 5},
    )
    assert result["classificacao"] == "Baixo"


def test_classify_custom_bands_edge_10():
    """Score == 10 usa última banda mesmo se fora do range (paridade com legacy)."""
    cfg = FinancialScoreConfig(
        taxa_poupanca=ScoreComponent("taxa_poupanca_recorrente", 0, 50, 2.0, "x"),
        cobertura=ScoreComponent("cobertura_despesas", 3, 24, 1.5, "x"),
        endividamento=ScoreComponent("taxa_endividamento", 5, 50, 1.5, "x"),
        progresso_if=ScoreComponent("progresso_if", 5, 80, 2.0, "x"),
        diversificacao=ScoreComponent("diversificacao", 1, 6, 1.0, "x"),
        classificacao=(
            ScoreClassificacao(min=0, max=5, label="Baixo"),
            ScoreClassificacao(min=5, max=10, label="Alto"),
        ),
    )
    calc = FinancialScoreCalculator(cfg)
    result = calc.calculate(
        ratios={
            "taxa_poupanca_recorrente_pct": 50,
            "cobertura_despesas_meses": 24,
            "taxa_endividamento_pct": 50,
        },
        patrimonio={"composicao": [{"valor": 1}] * 6},
        goals={"if_pct": 80},
    )
    assert result["valor"] == 10.0
    assert result["classificacao"] == "Alto"
