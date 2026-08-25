"""A40.l5 PR2: contrato E5 dos blocos que movem decisao no relatorio."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from backend.app.services.pipeline.pipeline_adapter import _alocacao_bundle_payload
from pipeline.domain.services.alocacao_derived_enricher import (
    enrich_alocacao_with_deviation,
)
from pipeline.domain.services.consumo_consciente_calculator import (
    ConsumoConscienteCalculator,
)
from pipeline.domain.services.e5_serialization import _enrich_goals_with_passive_income
from pipeline.domain.services.if_projector import IFProjection
from pipeline.domain.services.passive_income_calculator import PassiveIncomeResult
from pipeline.domain.services.patrimonio_types import MemberIdentity
from pipeline.domain.services.reserva_emergencia_calculator import (
    EmergencyReserveCalculator,
    ReservaEmergenciaConfig,
)
from pipeline.domain.services.reserva_liquidez import FallbackIrpfPorPapel
from scripts.pipeline_common import validate_dict
from tests.fixtures.e5_fluxo_minimo import FLUXO_CAIXA_MINIMO

_CONSUMO_FLUXO = {
    "janela_12m": {
        "receita_recorrente_mensal": 20_000,
        "despesa_mensal_media": 12_000,
        "n_meses": 12,
        "periodo": "2025-09 a 2026-08",
    }
}
_CONSUMO_DESPESAS = {
    "dados": {
        "lazer": [
            {
                "descricao": "Viagem sintetica",
                "banco": "Banco Teste",
                "tipo_conta": "cartao",
                "data": "2026-07-15",
                "valor": 3_000,
            }
        ]
    }
}


def _consumo_do_produtor() -> dict:
    result = ConsumoConscienteCalculator().calculate(_CONSUMO_FLUXO, _CONSUMO_DESPESAS)
    return result.to_legacy_dict()


def _reserva_do_produtor(*, com_renda_pj: bool = False) -> dict:
    identity = MemberIdentity(
        titular_key="titular",
        conjuge_key="",
        titular_nome="Titular",
        conjuge_nome="",
    )
    calculator = EmergencyReserveCalculator(ReservaEmergenciaConfig(members=identity))
    fluxo = {"despesa_mensal_media": 5_000, "janela_meses": 12}
    if com_renda_pj:
        fluxo["receita_por_natureza"] = {"receita_pj": 8_000, "receita_clt": 2_000}
    return calculator.calculate(
        fluxo=fluxo,
        patrimonio={"investimentos_titular": 30_000, "caixa_total_brl": 0},
        fallback_irpf=FallbackIrpfPorPapel(
            titular={
                "bens": {"investimentos": [{"descricao": "CDB LIQUIDEZ DIARIA", "valor": 30_000}]}
            }
        ),
    )


def _if_projection() -> IFProjection:
    return IFProjection(
        if_meta=1_000_000,
        if_trs=4,
        if_trs_monthly_value=3_333.33,
        if_pct=30,
        if_gap=700_000,
        prazo_anos_realista=12.5,
        idade_titular_if=53,
        ano_if=2039,
        renda_passiva_estimada_4pct=1_000,
        retorno_esperado_pct_aa=6,
        motivo_prazo_indefinido=None,
    )


def _alocacao_do_adapter() -> dict:
    return _alocacao_bundle_payload(
        {
            "rf_pos_pct": 20,
            "rf_pre_pct": 10,
            "rf_ipca_pct": 10,
            "acoes_br_pct": 25,
            "acoes_int_pct": 15,
            "fiis_pct": 10,
            "caixa_pct": 10,
            "rebalanceamento_modo": "por_aporte",
            "instrumentos": {"renda_fixa": "Tesouro Selic"},
        },
        converted_from="1",
    )


def _passive_income_ok() -> PassiveIncomeResult:
    return PassiveIncomeResult(
        Decimal("12000"),
        Decimal("1000"),
        {"dividendos": Decimal("12000")},
        Decimal("0"),
        Decimal("0"),
        Decimal("300000"),
        Decimal("4"),
        2025,
        8,
        Decimal("70"),
        "ok",
    )


def _goals_do_produtor() -> dict:
    goals = {**_if_projection().to_legacy_dict(), "alocacao_alvo": _alocacao_do_adapter()}
    goals = enrich_alocacao_with_deviation(
        goals,
        [{"categoria": "Renda Fixa", "valor": 100_000}],
    )
    return dict(_enrich_goals_with_passive_income(goals, _passive_income_ok()))


def _payload_real() -> dict:
    return {
        "score": {"valor": 7, "classificacao": "Bom"},
        "patrimonio": {"bruto": 1_000_000, "liquido": 900_000},
        "fluxo_caixa": FLUXO_CAIXA_MINIMO,
        "consumo_consciente": _consumo_do_produtor(),
        "reserva_emergencia": _reserva_do_produtor(),
        "goals": _goals_do_produtor(),
    }


@pytest.fixture(autouse=True)
def _strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


def test_payload_dos_produtores_reais_valida() -> None:
    goals = _payload_real()["goals"]
    passive_fields = {
        "taxa_retirada_efetiva_pct",
        "renda_passiva_anual_observada_brl",
        "renda_passiva_mensal_observada_brl",
        "patrimonio_gerador_brl",
        "acumuladores_pct_gerador",
        "ano_referencia_irpf",
        "defasagem_meses",
        "janela",
        "janela_meses",
    }

    assert passive_fields <= goals.keys()
    assert validate_dict(_payload_real(), "e5_analysis.schema.json") is True


def test_reserva_aceita_receita_pj_nula_e_numerica() -> None:
    payload = _payload_real()
    assert payload["reserva_emergencia"]["receita_pj_pct"] is None
    assert validate_dict(payload, "e5_analysis.schema.json") is True

    payload["reserva_emergencia"] = _reserva_do_produtor(com_renda_pj=True)
    assert payload["reserva_emergencia"]["receita_pj_pct"] == 80.0
    assert validate_dict(payload, "e5_analysis.schema.json") is True


def test_alocacao_reduzida_do_adapter_valida() -> None:
    payload = _payload_real()
    payload["goals"]["alocacao_alvo"] = {"_source": "db:goals"}

    assert validate_dict(payload, "e5_analysis.schema.json") is True


def test_campos_opcionais_podem_ser_omitidos() -> None:
    payload = _payload_real()
    del payload["goals"]["motivo_prazo_indefinido"]
    del payload["reserva_emergencia"]["niveis"]
    del payload["consumo_consciente"]["analise"]

    assert validate_dict(payload, "e5_analysis.schema.json") is True


@pytest.mark.parametrize(
    ("path", "orphan_key"),
    [
        (("consumo_consciente",), "pontuais_total"),
        (("reserva_emergencia",), "meses_cobertura"),
        (("reserva_emergencia", "composicao_liquida"), "investimentos_david"),
        (("reserva_emergencia", "excluido_da_reserva"), "outros"),
        (("goals",), "trs_pct"),
        (("goals", "alocacao_alvo"), "rebalanceamento_mode"),
        (("consumo_consciente", "itens", 0), "merchant"),
    ],
)
def test_leitura_orfa_falha_no_boundary(path: tuple[str | int, ...], orphan_key: str) -> None:
    payload = deepcopy(_payload_real())
    target = payload
    for part in path:
        target = target[part]
    target[orphan_key] = "campo que produtor nenhum emite"

    assert validate_dict(payload, "e5_analysis.schema.json") is False


def test_tipo_errado_no_item_de_consumo_falha() -> None:
    payload = _payload_real()
    payload["consumo_consciente"]["itens"][0]["valor"] = "3000"

    assert validate_dict(payload, "e5_analysis.schema.json") is False
