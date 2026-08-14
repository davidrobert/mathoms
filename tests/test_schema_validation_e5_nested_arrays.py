"""A40.l5 PR3: contratos producer-backed dos arrays aninhados do E5."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from pipeline.domain.services.exposicao_cambial_analyzer import compute_exposicao_cambial
from pipeline.domain.services.if_monte_carlo import (
    IFMonteCarloConfig,
    PrazoDeclarado,
    run_monte_carlo_if,
)
from pipeline.domain.services.if_monte_carlo_payload import monte_carlo_to_dict
from scripts.pipeline_common import validate_dict
from tests.fixtures.e5_fluxo_minimo import FLUXO_CAIXA_MINIMO


def _exposicao_cambial() -> dict:
    caixa = {
        "conta": "Conta sintética",
        "moeda": "USD",
        "saldo_original": 1_000,
        "valor_brl": 5_000,
    }
    posicao = {
        "tipo": "ETF Internacional",
        "descricao": "ETF sintético",
        "valor_atual": 25_000,
    }
    resultado = compute_exposicao_cambial(
        caixa_detalhes=[caixa],
        investimentos_atuais={"dados": [posicao]},
        investivel_financeiro=100_000,
    )
    return resultado.to_dict()


def _monte_carlo() -> dict:
    config = IFMonteCarloConfig(
        patrimonio_investivel=Decimal("800000"),
        meta_if=Decimal("1000000"),
        n_simulacoes=1_000,
        horizonte_simulado_anos=4,
        ano_base=2026,
    )
    prazo = PrazoDeclarado(anos=3, ano_alvo=2029, declarado_em="2026-08-14")
    return monte_carlo_to_dict(run_monte_carlo_if(config, 2026, prazo))


def _payload() -> dict:
    return {
        "score": {"valor": 7, "classificacao": "Bom"},
        "patrimonio": {"bruto": 1_000, "liquido": 900},
        "fluxo_caixa": FLUXO_CAIXA_MINIMO,
        "exposicao_cambial": _exposicao_cambial(),
        "if_monte_carlo": _monte_carlo(),
    }


@pytest.fixture(autouse=True)
def _strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


def test_arrays_aninhados_dos_produtores_reais_validam() -> None:
    payload = _payload()

    assert payload["exposicao_cambial"]["detalhes"]
    assert payload["if_monte_carlo"]["caminho_p50"]
    assert validate_dict(payload, "e5_analysis.schema.json") is True


@pytest.mark.parametrize("field", ["saldo_original", "valor_brl"])
def test_detalhe_cambial_rejeita_numero_nulo(field: str) -> None:
    payload = _payload()
    payload["exposicao_cambial"]["detalhes"][0][field] = None

    assert validate_dict(payload, "e5_analysis.schema.json") is False


def test_detalhe_cambial_rejeita_chave_que_produtor_nao_emite() -> None:
    payload = _payload()
    payload["exposicao_cambial"]["detalhes"][0]["fantasma"] = True

    assert validate_dict(payload, "e5_analysis.schema.json") is False


@pytest.mark.parametrize(
    "invalid_point",
    [[2026], [2026, 1_000, 2_000], ["2026", 1_000], [2026, None]],
)
def test_ponto_do_cone_rejeita_tupla_invalida(invalid_point: list[object]) -> None:
    payload = deepcopy(_payload())
    payload["if_monte_carlo"]["caminho_p50"][0] = invalid_point

    assert validate_dict(payload, "e5_analysis.schema.json") is False
