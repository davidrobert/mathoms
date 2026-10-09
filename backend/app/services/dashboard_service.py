"""Dashboard service — builds KPIs, charts, and alerts from E5 analysis JSON."""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from backend.app.schemas.dashboard import DashboardAlert, DashboardChart, DashboardKPI
from backend.app.services.storage.artifact_reader import read_latest_artifact
from pipeline.stage_spec import resolve_stage_name

logger = logging.getLogger(__name__)

_UM_DECIMAL = Decimal("0.1")


def load_e5_analysis(workspace_id: str, tenant_root: str) -> dict[str, Any] | None:
    """Lê E5 analysis do DB (preferência) com fallback em disco."""
    return read_latest_artifact(
        workspace_id,
        stage=resolve_stage_name("analyze_finances"),
        key="analise_financeira",
        tenant_root=tenant_root,
    )


def build_kpis(e5: dict[str, Any]) -> list[DashboardKPI]:
    candidatos = (
        _kpi_taxa_poupanca(e5.get("ratios") or {}),
        _kpi_score(e5.get("score") or {}),
    )
    return [kpi for kpi in candidatos if kpi is not None]


# Sem mês documentado a taxa sai 0 por divisão vazia — publicá-la seria um zero falso.
def _kpi_taxa_poupanca(ratios: dict[str, Any]) -> DashboardKPI | None:
    pct = _decimal_ou_none(ratios.get("taxa_poupanca_recorrente_pct"))
    meses = int(ratios.get("janela_meses") or 0)
    if pct is None or meses <= 0:
        return None
    return DashboardKPI(
        key="taxa_de_poupanca",
        label=f"Taxa de Poupança Recorrente · {_base_da_janela(meses)}",
        value=_fmt_pct(pct),
        raw_value=float(pct),
    )


def _kpi_score(score: dict[str, Any]) -> DashboardKPI | None:
    if not score:
        return None
    valor = score.get("valor", 0)
    return DashboardKPI(
        key="score_financeiro",
        label="Score Financeiro",
        value=f"{valor}/{score.get('max', 100)}",
        raw_value=float(valor),
    )


def _decimal_ou_none(valor: Any) -> Decimal | None:
    if valor is None:
        return None
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return None


# ADR-306 D1: KPI declara a própria base, e o N vem de `janela_meses`, nunca um 12 fixo.
def _base_da_janela(meses: int) -> str:
    if meses == 1:
        return "último mês documentado"
    return f"últimos {meses} meses documentados"


# ADR-209: o pct já é absoluto (44.7 = 44,7%) — nada de multiplicar por 100.
def _fmt_pct(pct: Decimal) -> str:
    arredondado = pct.quantize(_UM_DECIMAL, rounding=ROUND_HALF_UP)
    return f"{arredondado}".replace(".", ",") + "%"


def build_charts(e5: dict[str, Any]) -> list[DashboardChart]:
    charts: list[DashboardChart] = []

    fluxo = e5.get("fluxo_caixa", {})
    receita_desp = fluxo.get("receita_despesa_mensal_detalhado", {})
    if receita_desp.get("labels") and receita_desp.get("datasets"):
        charts.append(
            DashboardChart(
                chart_type="bar",
                title="Receita vs Despesa Mensal",
                data=receita_desp,
            )
        )

    despesas = _chart_despesas_por_categoria(fluxo.get("janela_12m") or {})
    if despesas is not None:
        charts.append(despesas)

    patrimonio = e5.get("patrimonio", {})
    composicao = patrimonio.get("composicao", {})
    if composicao:
        composicao_data = composicao if isinstance(composicao, dict) else {"items": composicao}
        charts.append(
            DashboardChart(
                chart_type="pie",
                title="Composição Patrimonial",
                data=composicao_data,
            )
        )

    investimentos = e5.get("investimentos", {})
    tabela_classes = investimentos.get("tabela_classes", [])
    if tabela_classes:
        charts.append(
            DashboardChart(
                chart_type="bar",
                title="Investimentos por Classe",
                data=_bar_data_por_classe(tabela_classes),
            )
        )

    return charts


# Chave crua de propósito: tirar o aporte (ADR-333 §Emenda) e humanizar o rótulo é do
# leitor, com `isAporteInvestimentoKey`/`humanizeCategoryLabel` — o mesmo do relatório.
def _chart_despesas_por_categoria(janela_12m: dict[str, Any]) -> DashboardChart | None:
    categorias = janela_12m.get("despesas_por_categoria") or {}
    if not categorias:
        return None
    return DashboardChart(
        chart_type="pie",
        title="Despesas por Categoria",
        data={
            "fonte": "despesas_por_categoria",
            "categorias": categorias,
            "janela_meses": janela_12m.get("janela_meses", 0),
        },
    )


def _bar_data_por_classe(tabela_classes: list[dict[str, Any]]) -> dict[str, Any]:
    # `valor`, nunca `pct`: imóvel com uso não apurado publica `pct` null (A40.l122).
    return {
        "labels": [classe["categoria"] for classe in tabela_classes],
        "datasets": [{"label": "Valor", "data": [classe["valor"] for classe in tabela_classes]}],
    }


def build_alerts(e5: dict[str, Any]) -> list[DashboardAlert]:
    alerts: list[DashboardAlert] = []

    for alerta_msg in e5.get("alertas", []):
        alerts.append(
            DashboardAlert(
                severity="warning",
                title="Alerta",
                message=alerta_msg,
            )
        )

    for ponto in e5.get("pontos_urgentes", []):
        if isinstance(ponto, dict):
            acao = ponto.get("acao", "")
            impacto = ponto.get("impacto", "")
            prazo = ponto.get("prazo", "")
            msg = acao
            if impacto:
                msg += f" — {impacto}"
            if prazo:
                msg += f" ({prazo})"
        else:
            msg = str(ponto)
        alerts.append(
            DashboardAlert(
                severity="critical",
                title="Ponto Urgente",
                message=msg,
            )
        )

    return alerts


def get_data_freshness(e5: dict[str, Any]) -> str | None:
    return e5.get("data_analise")


def get_periodo(e5: dict[str, Any]) -> str | None:
    periodo = e5.get("periodo_dados", {})
    if isinstance(periodo, dict):
        inicio = periodo.get("inicio", "")
        fim = periodo.get("fim", "")
        if inicio or fim:
            return f"{inicio} — {fim}"
    elif isinstance(periodo, str):
        return periodo
    return None
