"""A40.l5 PR3: contrato producer-backed do score consumido no relatório."""

from __future__ import annotations

from copy import deepcopy

import pytest

from pipeline.domain.services.financial_score_calculator import (
    FinancialScoreCalculator,
    FinancialScoreConfig,
)
from scripts.pipeline_common import validate_dict
from tests.fixtures.e5_fluxo_minimo import FLUXO_CAIXA_MINIMO


def _score() -> dict:
    calculator = FinancialScoreCalculator(FinancialScoreConfig.default())
    return calculator.calculate(
        ratios={
            "taxa_poupanca_recorrente_pct": 10,
            "autonomia_financeira_meses": 6,
            "taxa_endividamento_pct": 20,
        },
        patrimonio={"composicao": [{"valor": 100}]},
        goals={"if_pct": 20},
    )


def _payload(score: dict | None = None) -> dict:
    return {
        "score": score or _score(),
        "patrimonio": {"bruto": 1_000, "liquido": 900},
        "fluxo_caixa": FLUXO_CAIXA_MINIMO,
    }


@pytest.fixture(autouse=True)
def _strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


def test_score_do_produtor_real_valida() -> None:
    score = _score()

    assert score["breakdown"]
    assert score["context"]
    assert score["conclusion"]
    assert validate_dict(_payload(score), "e5_analysis.schema.json") is True


def test_score_legado_sem_campos_aditivos_continua_valido() -> None:
    legacy = {"valor": 7, "classificacao": "Bom"}

    assert validate_dict(_payload(legacy), "e5_analysis.schema.json") is True


@pytest.mark.parametrize("field", ["dimensao", "valor", "max", "peso", "contribuicao"])
def test_breakdown_rejeita_campo_obrigatorio_ausente(field: str) -> None:
    payload = deepcopy(_payload())
    del payload["score"]["breakdown"][0][field]

    assert validate_dict(payload, "e5_analysis.schema.json") is False


@pytest.mark.parametrize("invalid_value", [None, "dez"])
def test_breakdown_rejeita_valor_nao_numerico(invalid_value: object) -> None:
    payload = deepcopy(_payload())
    payload["score"]["breakdown"][0]["valor"] = invalid_value

    assert validate_dict(payload, "e5_analysis.schema.json") is False


def test_breakdown_rejeita_chave_que_produtor_nao_emite() -> None:
    payload = deepcopy(_payload())
    payload["score"]["breakdown"][0]["fantasma"] = True

    assert validate_dict(payload, "e5_analysis.schema.json") is False
