"""Dashboard service — builds KPIs, charts, and alerts from E5 analysis JSON."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.app.schemas.dashboard import DashboardAlert, DashboardChart, DashboardKPI

logger = logging.getLogger(__name__)


def load_e5_analysis(tenant_root: str) -> dict[str, Any] | None:
    path = Path(tenant_root) / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load E5 analysis: %s", exc)
        return None


def _fmt_brl(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"R$ {value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"R$ {value / 1_000:,.1f}k"
    return f"R$ {value:,.2f}"


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%" if value < 1 else f"{value:.1f}%"


def build_kpis(e5: dict[str, Any]) -> list[DashboardKPI]:
    kpis: list[DashboardKPI] = []

    score = e5.get("score", {})
    if score:
        score_val = score.get("valor", 0)
        score_max = score.get("max", 100)
        kpis.append(
            DashboardKPI(
                label="Score Financeiro",
                value=f"{score_val}/{score_max}",
                raw_value=float(score_val),
            )
        )

    patrimonio = e5.get("patrimonio", {})
    if patrimonio:
        liquido = patrimonio.get("liquido", 0)
        kpis.append(
            DashboardKPI(
                label="Patrimônio Líquido",
                value=_fmt_brl(liquido),
                raw_value=float(liquido),
            )
        )

    ratios = e5.get("ratios", {})
    if ratios:
        taxa_poup = ratios.get("taxa_poupanca", 0)
        kpis.append(
            DashboardKPI(
                label="Taxa de Poupança",
                value=_fmt_pct(taxa_poup),
                raw_value=float(taxa_poup),
            )
        )

    fluxo = e5.get("fluxo_caixa", {})
    if fluxo:
        receita_desp = fluxo.get("receita_despesa_mensal_detalhado", {})
        datasets = receita_desp.get("datasets", [])
        if len(datasets) >= 2:
            receita_total = sum(datasets[0].get("data", []))
            despesa_total = sum(datasets[1].get("data", []))
            if receita_total > 0 or despesa_total > 0:
                kpis.append(
                    DashboardKPI(
                        label="Receita vs Despesa",
                        value=f"{_fmt_brl(receita_total)} / {_fmt_brl(despesa_total)}",
                        raw_value=receita_total - despesa_total,
                    )
                )

    return kpis


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

    despesas_cat = fluxo.get("despesas_por_categoria", {})
    if despesas_cat:
        charts.append(
            DashboardChart(
                chart_type="pie",
                title="Despesas por Categoria",
                data=despesas_cat,
            )
        )

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
                data={"classes": tabela_classes, "total": investimentos.get("total", 0)},
            )
        )

    return charts


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
