"""Contrato dos alertas do dashboard: `build_alerts` (produtor) ↔ summary e cards do ``/plano``.

O summary fechado da "Análise Financeira" conta os pontos urgentes e só acende o tom
crítico com prioridade alta; aviso de qualidade de dado não entra na contagem. Par sobre a
fixture ``frontend/tests/fixtures/dashboard_alerts.json``: este lado assere que o produtor
emite exatamente a fixture; o lado TS (``frontend/tests/components/planoAnaliseFinanceira.test.tsx``)
assere o que o summary e os cards fazem com ela.

O E5 de cada cenário sai dos PRODUTORES REAIS (``PontosUrgentesAnalyzer``,
``partition_pontos_urgentes``, ``build_alertas``): um E5 escrito à mão repetiria a crença
do produtor e passaria. A fixture é GERADA, nunca escrita à mão. Para regravar após
mudança legítima de shape::

    MATHOMS_UPDATE_DASHBOARD_ALERTS_FIXTURE=1 \\
      .venv/bin/python -m pytest backend/tests/test_dashboard_alerts_contract.py -q
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from backend.app.schemas.dashboard import DashboardResponse
from backend.app.services.dashboard_service import build_alerts
from pipeline.domain.services.e5_serialization import build_alertas, partition_pontos_urgentes
from pipeline.domain.services.pontos_urgentes_analyzer import PontosUrgentesAnalyzer

_REPO = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO / "frontend" / "tests" / "fixtures" / "dashboard_alerts.json"
_UPDATE_ENV = "MATHOMS_UPDATE_DASHBOARD_ALERTS_FIXTURE"

_RATIOS_SAUDAVEIS = {"taxa_endividamento_pct": 5.0, "rentabilidade_pct": 6.0}
_RESERVA_OK = {"piso_cobertura_meses": 12.0}
_RESERVA_CURTA = {"piso_cobertura_meses": 2.0}
_GAP_VIDA = {
    "gap_qualitativo": [{"categoria": "vida", "flag": True, "rationale": "dependentes_menores_18"}]
}
_TRS_SUSPEITA = {"rentabilidade": {"status": "suspeito", "valor_pct": 14.2}}


def _e5(ratios: dict[str, Any], reserva: dict[str, Any], protecao: Any = None) -> dict[str, Any]:
    # `protecao=None` produz o seguro de vida `nao_verificavel`: retido, fora do ranking.
    itens = PontosUrgentesAnalyzer().analyze(ratios, reserva, {}, protecao)
    ranqueados, retidos = partition_pontos_urgentes([item.to_dict() for item in itens])
    return {
        "pontos_urgentes": ranqueados,
        "pontos_urgentes_retidos": retidos,
        "alertas": build_alertas({}, ratios),
    }


_CENARIOS: dict[str, dict[str, Any]] = {
    "sem_alerta": _e5(_RATIOS_SAUDAVEIS, _RESERVA_OK),
    "so_aviso": _e5({**_RATIOS_SAUDAVEIS, **_TRS_SUSPEITA}, _RESERVA_OK),
    "so_media": _e5({**_RATIOS_SAUDAVEIS, "rentabilidade_pct": "N/D"}, _RESERVA_OK),
    "com_alta": _e5(_RATIOS_SAUDAVEIS, _RESERVA_OK, _GAP_VIDA),
    "misto": _e5(
        {"taxa_endividamento_pct": 35.0, "rentabilidade_pct": "N/D"}, _RESERVA_CURTA, _GAP_VIDA
    ),
}


def _alertas_no_wire(e5: dict[str, Any]) -> list[dict[str, Any]]:
    response = DashboardResponse(kpis=[], charts=[], alerts=build_alerts(e5))
    return response.model_dump(mode="json")["alerts"]


def _fixture_gerada() -> dict[str, list[dict[str, Any]]]:
    return {nome: _alertas_no_wire(e5) for nome, e5 in _CENARIOS.items()}


def test_produtor_emite_exatamente_a_fixture_do_frontend():
    gerada = _fixture_gerada()
    if os.environ.get(_UPDATE_ENV) == "1":
        _FIXTURE.write_text(json.dumps(gerada, indent=2, ensure_ascii=False) + "\n")
    assert json.loads(_FIXTURE.read_text()) == gerada, f"regrave com {_UPDATE_ENV}=1"


def test_pontos_urgentes_vem_antes_dos_avisos():
    kinds = [a["kind"] for a in _alertas_no_wire(_CENARIOS["misto"])]
    assert kinds == ["ponto_urgente"] * 4 + ["aviso"]


def test_so_a_prioridade_alta_e_critical():
    alertas = _alertas_no_wire(_CENARIOS["misto"])
    prioridades = [p["prioridade"] for p in _CENARIOS["misto"]["pontos_urgentes"]]
    assert prioridades == ["Alta", "Alta", "Alta", "Média"]
    assert [a["severity"] for a in alertas] == ["critical"] * 3 + ["warning"] * 2


@pytest.mark.parametrize(
    ("prioridade", "severity"),
    [("Crítica", "critical"), (None, "critical"), ("", "critical"), ("media", "warning")],
)
def test_prioridade_fora_do_vocabulario_conta_como_alta(prioridade: Any, severity: str):
    (alerta,) = build_alerts({"pontos_urgentes": [{"acao": "Agir", "prioridade": prioridade}]})
    assert alerta.severity == severity


def test_ponto_urgente_retido_nao_chega_ao_dashboard():
    e5 = _CENARIOS["sem_alerta"]
    assert [r["code"] for r in e5["pontos_urgentes_retidos"]] == ["seguro_vida"]
    assert _alertas_no_wire(e5) == []


@pytest.mark.parametrize("nome", list(_CENARIOS))
def test_contagem_de_pontos_urgentes_bate_com_o_s10(nome: str):
    e5 = _CENARIOS[nome]
    urgentes = [a for a in _alertas_no_wire(e5) if a["kind"] == "ponto_urgente"]
    assert len(urgentes) == len(e5["pontos_urgentes"])


def test_aviso_de_qualidade_de_dado_se_chama_aviso():
    (aviso,) = _alertas_no_wire(_CENARIOS["so_aviso"])
    assert (aviso["kind"], aviso["severity"], aviso["title"]) == ("aviso", "warning", "Aviso")
