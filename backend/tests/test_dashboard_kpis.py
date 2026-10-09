"""KPIs do dashboard (``/plano`` › Mês corrente) contra o E5 dos produtores reais.

"Taxa de Poupança" lia ``ratios.taxa_poupanca``, que o E5 não emite — 0,0% para toda
família —, e "Receita vs Despesa" lia um ``datasets`` que nunca existiu. Mesma classe de
defeito dos gráficos: o E5 vem de ``backend/tests/helpers/dashboard_e5.py``, montado pelos
produtores, porque um E5 escrito à mão repetiria a crença do produtor e passaria.
"""

from __future__ import annotations

from backend.app.services.dashboard_service import build_kpis
from backend.tests.helpers.dashboard_e5 import e5_sintetico

_E5 = e5_sintetico()


def _taxa_com(**ratios: object):
    (taxa,) = build_kpis({"ratios": {**_E5["ratios"], **ratios}})
    return taxa


def test_taxa_de_poupanca_le_o_campo_que_o_e5_emite():
    taxa = build_kpis(_E5)[0]
    assert taxa.key == "taxa_de_poupanca"
    assert taxa.label == "Taxa de Poupança Recorrente · últimos 12 meses documentados"
    assert taxa.value == "55,0%"
    assert taxa.raw_value == _E5["ratios"]["taxa_poupanca_recorrente_pct"]


def test_so_sobram_taxa_de_poupanca_e_score():
    # Saem a soma da janela sem rótulo (ADR-306 D1) e o patrimônio que já está no
    # PlanoKpiRow, lido do snapshot do relatório (ADR-156): dois patrimônios na página.
    assert [kpi.key for kpi in build_kpis(_E5)] == ["taxa_de_poupanca", "score_financeiro"]


def test_base_no_singular_com_um_mes_documentado():
    taxa = _taxa_com(janela_meses=1)
    assert taxa.label == "Taxa de Poupança Recorrente · último mês documentado"


def test_taxa_negativa_nao_multiplica_por_cem():
    assert _taxa_com(taxa_poupanca_recorrente_pct=-12.0).value == "-12,0%"


def test_pct_que_chega_como_string_formata_igual():
    assert _taxa_com(taxa_poupanca_recorrente_pct="50.000000").value == "50,0%"


def test_sem_mes_documentado_nao_publica_zero_falso():
    ratios = {**_E5["ratios"], "janela_meses": 0, "taxa_poupanca_recorrente_pct": 0.0}
    assert build_kpis({"ratios": ratios}) == []
