"""Testes unitários do mapper DTO do agregado Goal (4 tipos).

Cobrem:

- ``goal_to_typed_response`` resolve o response correto a partir de
  ``goal.type`` (IF, Aporte, Dólar, Alocação).
- ``goal_to_if_response`` é atalho narrow para IF (compat legado).
- ``meta_version_from_params`` com fallbacks para dados inválidos.
- ``GOAL_TYPE_DTO_CLASSES`` tem os 4 tipos registrados.
- Mapper funciona sem ``AsyncSession``.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from backend.app.schemas.dto.goal import (
    AlocacaoGoalResponse,
    AporteGoalResponse,
    DolarGoalResponse,
    GOAL_TYPE_DTO_CLASSES,
    IFGoalResponse,
    goal_to_if_response,
    goal_to_typed_response,
    meta_version_from_params,
)


def _fake_goal(type_str: str, params_inputs: dict, derived_json: dict) -> SimpleNamespace:
    """Monta um 'ORM Goal' fake com atributos que o mapper lê."""
    return SimpleNamespace(
        id=f"goal-{type_str}",
        workspace_id="ws-1",
        type=type_str,
        params_json={"inputs": params_inputs, "meta_version": 1},
        derived_json=derived_json,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_template=False,
        notes=None,
        created_by="user-1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


IF_INPUTS = {
    "renda_passiva_mensal_brl": 30000,
    "trs_pct": 5.0,
    "retorno_real_anual_pct": 5.0,
    "horizonte_anos": 15,
    "taxa_retirada_conservadora_pct": 4.0,
}
IF_DERIVED = {
    "if_meta_brl": 7200000.0,
    "aporte_necessario_mensal_brl": 30000.0,
    "if_meta_conservadora_brl": 9000000.0,
}


class TestGOAL_TYPE_DTO_CLASSES:
    def test_all_four_types_registered(self):
        assert set(GOAL_TYPE_DTO_CLASSES.keys()) == {
            "INDEPENDENCIA_FINANCEIRA",
            "APORTE_MENSAL",
            "DOLARIZACAO",
            "ALOCACAO_ALVO",
        }


class TestMetaVersionFromParams:
    def test_none_params_returns_1(self):
        assert meta_version_from_params(None) == 1

    def test_empty_dict_returns_1(self):
        assert meta_version_from_params({}) == 1

    def test_missing_key_returns_1(self):
        assert meta_version_from_params({"inputs": {}}) == 1

    def test_valid_int_returns_as_is(self):
        assert meta_version_from_params({"meta_version": 3}) == 3

    def test_string_digit_coerces_to_int(self):
        assert meta_version_from_params({"meta_version": "2"}) == 2

    def test_none_value_falls_back_to_1(self):
        assert meta_version_from_params({"meta_version": None}) == 1

    def test_invalid_string_falls_back_to_1(self):
        assert meta_version_from_params({"meta_version": "abc"}) == 1


class TestGoalToTypedResponse:
    def test_if_goal(self):
        goal = _fake_goal("INDEPENDENCIA_FINANCEIRA", IF_INPUTS, IF_DERIVED)

        resp = goal_to_typed_response(goal, created_by_name="Alice")

        assert isinstance(resp, IFGoalResponse)
        assert resp.type == "INDEPENDENCIA_FINANCEIRA"
        assert resp.inputs.renda_passiva_mensal_brl == 30000
        assert resp.derived.if_meta_brl == 7200000.0
        assert resp.created_by_name == "Alice"
        assert resp.meta_version == 1

    def test_aporte_goal(self):
        inputs = {
            "meta_aporte_mensal_brl": 5000.0,
            "dia_aporte": 5,
            "periodo_inicio": "Imediato",
            "distribuicao": {},
        }
        derived = {"aporte_anual_brl": 60000.0, "distribuicao_pct": {}}
        goal = _fake_goal("APORTE_MENSAL", inputs, derived)

        resp = goal_to_typed_response(goal)

        assert isinstance(resp, AporteGoalResponse)
        assert resp.type == "APORTE_MENSAL"
        assert resp.inputs.meta_aporte_mensal_brl == 5000.0
        assert resp.derived.aporte_anual_brl == 60000.0

    def test_dolar_goal(self):
        inputs = {"meta_usd": 100000.0, "aporte_mensal_brl": 2000.0}
        derived = {"horizonte_estimado_meses": 285.0}
        goal = _fake_goal("DOLARIZACAO", inputs, derived)

        resp = goal_to_typed_response(goal)

        assert isinstance(resp, DolarGoalResponse)
        assert resp.type == "DOLARIZACAO"
        assert resp.inputs.meta_usd == 100000.0

    def test_alocacao_goal(self):
        inputs = {
            "renda_fixa_pct": 40,
            "acoes_pct": 35,
            "imoveis_reits_pct": 15,
            "liquidez_usd_pct": 10,
            "instrumentos_rf": "CDB",
            "instrumentos_rv": "VT",
            "rebalanceamento": "anual",
        }
        derived = {"soma_percentuais": 100.0}
        goal = _fake_goal("ALOCACAO_ALVO", inputs, derived)

        resp = goal_to_typed_response(goal)

        assert isinstance(resp, AlocacaoGoalResponse)
        assert resp.derived.soma_percentuais == 100.0

    def test_unknown_type_raises_keyerror(self):
        goal = _fake_goal("UNKNOWN_TYPE", IF_INPUTS, IF_DERIVED)

        with pytest.raises(KeyError):
            goal_to_typed_response(goal)

    def test_created_by_name_optional(self):
        goal = _fake_goal("INDEPENDENCIA_FINANCEIRA", IF_INPUTS, IF_DERIVED)

        resp = goal_to_typed_response(goal)

        assert resp.created_by_name is None


class TestGoalToIFResponse:
    def test_if_goal(self):
        goal = _fake_goal("INDEPENDENCIA_FINANCEIRA", IF_INPUTS, IF_DERIVED)

        resp = goal_to_if_response(goal, created_by_name="Bob")

        # Retorno narrow — callers podem confiar que é IF.
        assert isinstance(resp, IFGoalResponse)
        assert resp.created_by_name == "Bob"

    def test_non_if_type_raises_assertion(self):
        """``goal_to_if_response`` é atalho narrow. Se o tipo não é IF,
        falha no assert — comportamento defensivo para caller errado."""
        inputs = {
            "meta_aporte_mensal_brl": 5000.0,
            "dia_aporte": 5,
            "periodo_inicio": "Imediato",
            "distribuicao": {},
        }
        derived = {"aporte_anual_brl": 60000.0, "distribuicao_pct": {}}
        goal = _fake_goal("APORTE_MENSAL", inputs, derived)

        with pytest.raises(AssertionError):
            goal_to_if_response(goal)
