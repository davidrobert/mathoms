"""Seed de alocação-alvo grava v2 canônico (ADR-141 §Emenda, A12.alocacao-v2 PR5).

Trava a regressão: o seed antigo gravava shape órfão {rf_pct, rv_pct,
alternativos_pct} com meta_version=1 — origem do bug que quebrava
GET /goals/alocacao.
"""

from __future__ import annotations

import pytest

from backend.app.schemas.dto.goal import ALOCACAO_V2_CLASS_FIELDS, AlocacaoGoalInputsV2
from backend.app.schemas.dto.goal.alocacao_shape_conversion import detect_alocacao_shape
from backend.app.scripts.seed_goals_workspace import (
    _DEFAULT_ALOCACAO_PARAMS,
    _DEMO_ALOCACAO_PARAMS,
    _build_goal,
)

_ALOCACAO_PARAMS = [_DEFAULT_ALOCACAO_PARAMS, _DEMO_ALOCACAO_PARAMS]


@pytest.mark.parametrize("params", _ALOCACAO_PARAMS)
def test_seed_params_sao_v2_validos_soma_100(params):
    assert detect_alocacao_shape(params) == "v2"
    modelo = AlocacaoGoalInputsV2(**params)
    assert sum(getattr(modelo, campo) for campo in ALOCACAO_V2_CLASS_FIELDS) == 100


@pytest.mark.parametrize("params", _ALOCACAO_PARAMS)
def test_seed_nao_grava_shape_orfao_legado(params):
    # Regressão: nenhuma chave do shape órfão antigo.
    assert not ({"rf_pct", "rv_pct", "alternativos_pct"} & set(params))


def test_build_goal_alocacao_carimba_meta_version_2_e_deriva():
    goal = _build_goal("ws-1", "ALOCACAO_ALVO", _DEFAULT_ALOCACAO_PARAMS, "seed")
    assert goal.params_json["meta_version"] == 2
    assert goal.derived_json["soma_percentuais"] == 100


def test_build_goal_outros_tipos_seguem_meta_version_1():
    goal = _build_goal("ws-1", "DOLARIZACAO", {"meta_usd": 10_000}, "seed")
    assert goal.params_json["meta_version"] == 1
    assert goal.derived_json == {}
