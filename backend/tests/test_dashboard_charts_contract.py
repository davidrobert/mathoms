"""Contrato do bar chart do dashboard: `build_charts` (produtor) ↔ `normalizeBarData` (leitor).

Par sobre uma fixture compartilhada, ``frontend/tests/fixtures/dashboard_charts.json``:
este lado assere que o produtor emite exatamente a fixture; o lado TS
(``frontend/tests/lib/dashboardCharts.test.ts``) assere que o leitor tira barras
dela. "Investimentos por Classe" saía com ``{classes, total}``, o leitor só lê
``{labels, datasets}`` e o card do ``/plano`` renderizava título sem barras: cada lado
tinha a sua crença do contrato e nenhum teste ligava as duas.

A fixture é GERADA pelo produtor, nunca escrita à mão (lição da A40.l3). Para regravar
após mudança legítima de shape::

    MATHOMS_UPDATE_DASHBOARD_CHARTS_FIXTURE=1 \\
      .venv/bin/python -m pytest backend/tests/test_dashboard_charts_contract.py -q
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from backend.app.schemas.dashboard import DashboardResponse
from backend.app.services.dashboard_service import build_charts

_REPO = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO / "frontend" / "tests" / "fixtures" / "dashboard_charts.json"
_UPDATE_ENV = "MATHOMS_UPDATE_DASHBOARD_CHARTS_FIXTURE"

# Valores sintéticos. A última linha antecipa a A40.l122: imóvel com uso não apurado
# publica `pct` null — o gráfico plota `valor` e não pode depender de `pct`.
_E5: dict[str, Any] = {
    "investimentos": {
        "tabela_classes": [
            {
                "categoria": "Renda Fixa",
                "valor": 300000.0,
                "pct": 40.0,
                "pct_carteira_financeira": 75.0,
            },
            {
                "categoria": "Imóveis Investimento",
                "valor": 200000.0,
                "pct": 26.67,
                "pct_carteira_financeira": None,
            },
            {
                "categoria": "Ações BR",
                "valor": 100000.0,
                "pct": 13.33,
                "pct_carteira_financeira": 25.0,
            },
            {
                "categoria": "Imóveis com uso não apurado",
                "valor": 150000.0,
                "pct": None,
                "pct_carteira_financeira": None,
            },
        ],
        "total": 750000.0,
    }
}


def _charts_no_wire(e5: dict[str, Any]) -> list[dict[str, Any]]:
    response = DashboardResponse(kpis=[], charts=build_charts(e5), alerts=[])
    return response.model_dump(mode="json")["charts"]


def test_investimentos_por_classe_sai_no_shape_que_o_leitor_le():
    (chart,) = _charts_no_wire(_E5)
    assert chart["chart_type"] == "bar"
    assert chart["data"] == {
        "labels": ["Renda Fixa", "Imóveis Investimento", "Ações BR", "Imóveis com uso não apurado"],
        "datasets": [{"label": "Valor", "data": [300000.0, 200000.0, 100000.0, 150000.0]}],
    }


def test_fixture_compartilhada_e_a_saida_do_produtor():
    charts = _charts_no_wire(_E5)
    if os.environ.get(_UPDATE_ENV) == "1":
        payload = json.dumps({"charts": charts}, ensure_ascii=False, indent=2) + "\n"
        _FIXTURE.write_text(payload, encoding="utf-8")
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert fixture == {"charts": charts}, f"fixture desatualizada; regrave com {_UPDATE_ENV}=1"
