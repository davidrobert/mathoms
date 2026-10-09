"""ADR-167 — o chart do cenário do cônjuge só existe para quem o E5 publicou."""

from __future__ import annotations

from pipeline.domain.services.narrativas.format_helpers import validate_narrativas
from tests.unit.pipeline.test_narrativas_l51 import _payload


def _payload_com_charts_proprios() -> dict:
    # `_payload` devolve o `_CHARTS` do módulo por referência: mutar sem copiar
    # vaza para os testes da l51 que rodam depois.
    payload = _payload()
    payload["charts"] = dict(payload["charts"])
    return payload


def test_narrativas_sem_o_chart_do_cenario_sao_validas():
    # Solteiro e workspace sem meta IF recebem `cenarios_conjuge: {}`; exigir o
    # chart reprovava o E5.N inteiro de todos eles.
    payload = _payload_com_charts_proprios()
    del payload["charts"]["cenarios_conjuge"]

    ok, errors = validate_narrativas(payload)

    assert ok, errors


def test_chart_do_cenario_presente_continua_exigindo_conclusao():
    payload = _payload_com_charts_proprios()
    payload["charts"]["cenarios_conjuge"] = {"context": "ctx", "conclusion": ""}

    ok, errors = validate_narrativas(payload)

    assert ok is False
    assert "charts.cenarios_conjuge.conclusion is missing or empty" in errors
