"""Pydantic schemas for Dashboard endpoints."""

from typing import Any, Literal, Optional

from pydantic import BaseModel


class DashboardKPI(BaseModel):
    # Identidade estável do KPI: o leitor escolhe o ícone por ela, não pela posição — o
    # produtor omite KPI sem dado, e a posição deslizaria o ícone para o vizinho.
    key: str
    label: str
    value: str
    raw_value: float
    delta: Optional[float] = None
    delta_percent: Optional[float] = None


class DashboardChart(BaseModel):
    chart_type: str
    title: str
    data: dict[str, Any]


class DashboardAlert(BaseModel):
    # `kind` é a origem do item no E5 e é o que o summary fechado da "Análise Financeira"
    # conta; `severity` é o tom, e só o ponto urgente de prioridade alta é `critical`.
    kind: Literal["ponto_urgente", "aviso"]
    severity: Literal["critical", "warning"]
    title: str
    message: str


class DashboardResponse(BaseModel):
    kpis: list[DashboardKPI]
    charts: list[DashboardChart]
    alerts: list[DashboardAlert]
    data_freshness: Optional[str] = None
    periodo: Optional[str] = None
