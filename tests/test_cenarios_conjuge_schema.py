"""Contrato E5 do aporte no cenário "Sem renda do cônjuge": ausência é null, nunca 0 (ADR-373)."""

from __future__ import annotations

import copy
import json

import pytest

from scripts.pipeline_common import validate_artifact
from tests.fixtures.e5_fluxo_minimo import FLUXO_CAIXA_MINIMO
from tests.test_schema_validation import _CENARIOS_CONJUGE_VALID

_CAMPOS_DE_APORTE = ("aportes", "aporte_mensal", "aporte_base")


def _cenarios_conjuge_aporte(valor, *campos):
    """``_CENARIOS_CONJUGE_VALID`` com ``valor`` nos campos de aporte (todos, sem ``campos``)."""
    alvo = set(campos or _CAMPOS_DE_APORTE)
    payload = copy.deepcopy(_CENARIOS_CONJUGE_VALID)
    if "aportes" in alvo:
        payload["aportes"] = [valor]
    if "aporte_mensal" in alvo:
        payload["cenarios"][0]["aporte_mensal"] = valor
    if "aporte_base" in alvo:
        payload["premissas"]["aporte_base"] = valor
    return payload


def _valida_e5(tmp_path, cenarios) -> bool:
    path = tmp_path / "e5.json"
    payload = {
        "score": {"valor": 6.8, "classificacao": "Bom"},
        "patrimonio": {"bruto": 5000000, "liquido": 4000000},
        "fluxo_caixa": FLUXO_CAIXA_MINIMO,
        "cenarios_conjuge": cenarios,
    }
    path.write_text(json.dumps(payload))
    return validate_artifact(path, "e5_analysis.schema.json")


def test_aporte_nao_declarado_sai_como_null_nos_tres_campos(tmp_path, monkeypatch):
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    assert _valida_e5(tmp_path, _cenarios_conjuge_aporte(None)) is True


@pytest.mark.parametrize("campo", _CAMPOS_DE_APORTE)
def test_aporte_zero_e_recusado(tmp_path, monkeypatch, campo):
    """Zero não é declarável: publicá-lo afirmaria um aporte que não existe."""
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    assert _valida_e5(tmp_path, _cenarios_conjuge_aporte(0.0, campo)) is False
