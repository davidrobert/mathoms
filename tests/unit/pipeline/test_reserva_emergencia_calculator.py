"""Testes para :class:`EmergencyReserveCalculator` (A6d.3.3 — ADR-100)."""

from __future__ import annotations

import pytest

from pipeline.domain.services.patrimonio_types import MemberIdentity
from pipeline.domain.services.reserva_emergencia_calculator import (
    EmergencyReserveCalculator,
    ReservaClassificacao,
    ReservaEmergenciaConfig,
)


@pytest.fixture
def identity() -> MemberIdentity:
    return MemberIdentity(
        titular_key="david",
        conjuge_key="mariana",
        titular_nome="David",
        conjuge_nome="Mariana",
    )


@pytest.fixture
def config(identity: MemberIdentity) -> ReservaEmergenciaConfig:
    return ReservaEmergenciaConfig(members=identity)


# =============================================================================
# ReservaEmergenciaConfig.from_scoring_json
# =============================================================================


def test_config_from_scoring_json_uses_defaults_when_empty(identity: MemberIdentity):
    cfg = ReservaEmergenciaConfig.from_scoring_json({}, identity)
    assert cfg.niveis_meses == (6, 12)
    assert len(cfg.classificacao) == 3
    assert cfg.classificacao[0].label == "Excelente"


def test_config_from_scoring_json_custom(identity: MemberIdentity):
    scoring = {
        "reserva_emergencia": {
            "niveis_meses": [3, 6, 12],
            "classificacao": [
                {"minimo_meses": 24, "label": "Supra"},
                {"minimo_meses": 6, "label": "OK"},
            ],
        }
    }
    cfg = ReservaEmergenciaConfig.from_scoring_json(scoring, identity)
    assert cfg.niveis_meses == (3, 6, 12)
    assert cfg.classificacao[0].label == "Supra"
    assert cfg.classificacao[0].minimo_meses == 24


# =============================================================================
# Cobertura
# =============================================================================


def test_cobertura_meses_computed(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    fluxo = {"despesa_mensal_media": 10_000}
    patrimonio = {
        "investimentos_david": 30_000,
        "investimentos_mariana": 20_000,
        "caixa_moeda_estrangeira": 10_000,
    }
    result = calc.calculate(fluxo=fluxo, patrimonio=patrimonio)
    # 60k / 10k = 6 meses
    assert result["cobertura_meses"] == 6.0
    assert result["total_liquida"] == 60_000.0


def test_cobertura_zero_despesa_returns_zero(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 0},
        patrimonio={
            "investimentos_david": 100,
            "investimentos_mariana": 0,
            "caixa_moeda_estrangeira": 0,
        },
    )
    assert result["cobertura_meses"] == 0.0


def test_niveis_sized_from_despesa(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 5_000},
        patrimonio={
            "investimentos_david": 0,
            "investimentos_mariana": 0,
            "caixa_moeda_estrangeira": 0,
        },
    )
    assert result["nivel_6_meses"] == 30_000.0
    assert result["nivel_12_meses"] == 60_000.0


# =============================================================================
# Classificação
# =============================================================================


def test_avaliacao_excelente_at_12_meses(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1000},
        patrimonio={
            "investimentos_david": 12_000,
            "investimentos_mariana": 0,
            "caixa_moeda_estrangeira": 0,
        },
    )
    assert result["avaliacao_liquidity"] == "Excelente"


def test_avaliacao_adequada_at_6_meses(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1000},
        patrimonio={
            "investimentos_david": 6_000,
            "investimentos_mariana": 0,
            "caixa_moeda_estrangeira": 0,
        },
    )
    assert result["avaliacao_liquidity"] == "Adequada"


def test_avaliacao_insuficiente_below_6_meses(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1000},
        patrimonio={
            "investimentos_david": 2_000,
            "investimentos_mariana": 0,
            "caixa_moeda_estrangeira": 0,
        },
    )
    assert result["avaliacao_liquidity"] == "Insuficiente"


def test_avaliacao_custom_bands(identity: MemberIdentity):
    """Config custom com banda 'Supra' em 24 meses."""
    cfg = ReservaEmergenciaConfig(
        members=identity,
        classificacao=(
            ReservaClassificacao(minimo_meses=24, label="Supra"),
            ReservaClassificacao(minimo_meses=0, label="Atenção"),
        ),
    )
    calc = EmergencyReserveCalculator(cfg)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1000},
        patrimonio={
            "investimentos_david": 30_000,
            "investimentos_mariana": 0,
            "caixa_moeda_estrangeira": 0,
        },
    )
    assert result["avaliacao_liquidity"] == "Supra"


def test_output_shape(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1000},
        patrimonio={
            "investimentos_david": 1000,
            "investimentos_mariana": 500,
            "caixa_moeda_estrangeira": 500,
        },
    )
    assert set(result.keys()) == {
        "despesas_mensais",
        "nivel_6_meses",
        "nivel_12_meses",
        "composicao_liquida",
        "total_liquida",
        "cobertura_meses",
        "avaliacao_liquidity",
        "niveis",
    }
    assert result["niveis"] == ["6 meses", "12 meses"]


def test_composicao_liquida_keys_dynamic(identity: MemberIdentity):
    """composicao_liquida usa identity dinâmica."""
    solo = MemberIdentity(titular_key="joao", conjuge_key="", titular_nome="João", conjuge_nome="")
    cfg = ReservaEmergenciaConfig(members=solo)
    calc = EmergencyReserveCalculator(cfg)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1000},
        patrimonio={
            "investimentos_joao": 5_000,
            "caixa_moeda_estrangeira": 1_000,
        },
    )
    assert "investimentos_joao" in result["composicao_liquida"]
    assert result["total_liquida"] == 6_000.0


def test_composicao_liquida_values_rounded(config: ReservaEmergenciaConfig):
    calc = EmergencyReserveCalculator(config)
    result = calc.calculate(
        fluxo={"despesa_mensal_media": 1000},
        patrimonio={
            "investimentos_david": 1000.123,
            "investimentos_mariana": 0.456,
            "caixa_moeda_estrangeira": 0.789,
        },
    )
    # Todos arredondados a 2 casas
    assert result["composicao_liquida"]["investimentos_david"] == 1000.12
    assert result["composicao_liquida"]["investimentos_mariana"] == 0.46
    assert result["composicao_liquida"]["caixa_moeda_estrangeira"] == 0.79
