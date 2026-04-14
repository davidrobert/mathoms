"""Pydantic schemas for Dashboard endpoints."""

from typing import Any, Optional

from pydantic import BaseModel


class DashboardKPI(BaseModel):
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
    severity: str
    title: str
    message: str


class DashboardResponse(BaseModel):
    kpis: list[DashboardKPI]
    charts: list[DashboardChart]
    alerts: list[DashboardAlert]
    data_freshness: Optional[str] = None
    periodo: Optional[str] = None
