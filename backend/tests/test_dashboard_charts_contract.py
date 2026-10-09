"""Contrato dos gráficos do dashboard: `build_charts` (produtor) ↔ leitores TS de barra e pizza.

Par sobre uma fixture compartilhada, ``frontend/tests/fixtures/dashboard_charts.json``:
este lado assere que o produtor emite exatamente a fixture; o lado TS
(``frontend/tests/lib/dashboardCharts.test.ts``) assere que os leitores tiram barras e
fatias dela. Três cards do ``/plano`` saíam vazios, cada lado com a sua crença do
contrato e nenhum teste ligando as duas: "Investimentos por Classe" (``{classes, total}``),
"Composição Patrimonial" (``{items}``) e "Receita vs Despesa Mensal", que lia um
``datasets`` que o E5 nunca emitiu.

O último mostra por que o E5 do par sai dos PRODUTORES REAIS (``FluxoCaixaEnricher``,
``build_composicao``, ``RatiosCalculator``): um E5 escrito à mão é a mesma crença do
produtor, e passaria. A fixture é GERADA, nunca escrita à mão (lição da A40.l3). Para
regravar após mudança legítima de shape::

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
from backend.tests.helpers.dashboard_e5 import e5_sintetico

_REPO = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO / "frontend" / "tests" / "fixtures" / "dashboard_charts.json"
_UPDATE_ENV = "MATHOMS_UPDATE_DASHBOARD_CHARTS_FIXTURE"
_E5 = e5_sintetico()


def _charts_no_wire(e5: dict[str, Any]) -> dict[str, dict[str, Any]]:
    response = DashboardResponse(kpis=[], charts=build_charts(e5), alerts=[])
    return {chart["title"]: chart for chart in response.model_dump(mode="json")["charts"]}


def test_investimentos_por_classe_sai_no_shape_que_o_leitor_le():
    chart = _charts_no_wire(_E5)["Investimentos por Classe"]
    assert chart["chart_type"] == "bar"
    assert chart["data"] == {
        "labels": ["Renda Fixa", "Imóveis Investimento", "Ações BR", "Imóveis com uso não apurado"],
        "datasets": [{"label": "Valor", "data": [300000.0, 200000.0, 100000.0, 150000.0]}],
    }


def test_receitas_e_saidas_sai_no_shape_do_leitor_de_barras():
    data = _charts_no_wire(_E5)["Receitas e Saídas por Mês"]["data"]
    mensal = _E5["fluxo_caixa"]["receita_despesa_mensal_detalhado"]
    assert data["x_axis"] == "month"
    assert data["labels"] == [f"2025-{m:02d}" for m in range(3, 13)] + ["2026-01", "2026-02"]
    assert data["datasets"] == [
        {"label": "Receitas", "tone": "gain", "data": mensal["totais_receita"][-12:]},
        {
            "label": "Saídas (inclui aportes)",
            "tone": "neutral",
            "data": mensal["totais_despesa"][-12:],
        },
    ]


def test_mes_fora_do_formato_do_e5_passa_cru():
    e5 = {"fluxo_caixa": {"receita_despesa_mensal_detalhado": {"labels": ["26/02", "2026"]}}}
    data = _charts_no_wire(e5)["Receitas e Saídas por Mês"]["data"]
    assert data["labels"] == ["2026-02", "2026"]


def test_composicao_sai_crua_para_o_predicado_unico_do_leitor():
    chart = _charts_no_wire(_E5)["Composição Patrimonial"]
    assert chart["chart_type"] == "pie"
    assert chart["data"] == {
        "fonte": "composicao_patrimonial",
        "composicao": _E5["patrimonio"]["composicao"],
    }


def test_composicao_fora_do_formato_lista_nao_vira_grafico():
    e5 = {"patrimonio": {"composicao": {"Residência": 0.0}}}
    assert "Composição Patrimonial" not in _charts_no_wire(e5)


def test_despesas_por_categoria_le_a_janela_12m_e_nao_o_periodo_inteiro():
    data = _charts_no_wire(_E5)["Despesas por Categoria"]["data"]
    janela = _E5["fluxo_caixa"]["janela_12m"]
    assert data == {
        "fonte": "despesas_por_categoria",
        "categorias": janela["despesas_por_categoria"],
        "janela_meses": 12,
    }
    assert data["categorias"] != _E5["fluxo_caixa"]["despesas_por_categoria"]


# `conferencia` leva ao lado TS o número do E5 contra o qual ele confere o que o seu
# predicado de aporte tirou da pizza — o par dos dois lados de "o que é aporte".
def test_fixture_compartilhada_e_a_saida_do_produtor():
    janela = _E5["fluxo_caixa"]["janela_12m"]
    esperado = {
        "charts": list(_charts_no_wire(_E5).values()),
        "conferencia": {
            "fluxo_caixa.janela_12m.transferencia_patrimonial": janela["transferencia_patrimonial"]
        },
    }
    if os.environ.get(_UPDATE_ENV) == "1":
        payload = json.dumps(esperado, ensure_ascii=False, indent=2) + "\n"
        _FIXTURE.write_text(payload, encoding="utf-8")
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert fixture == esperado, f"fixture desatualizada; regrave com {_UPDATE_ENV}=1"
