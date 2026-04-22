"""Dashboard API — KPIs, charts, and alerts from E5 analysis (tenant-scoped, ADR-072)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace
from backend.app.schemas.dashboard import DashboardAlert, DashboardResponse
from backend.app.services.dashboard_service import (
    build_alerts,
    build_charts,
    build_kpis,
    get_data_freshness,
    get_periodo,
    load_e5_analysis,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/dashboard",
    tags=["dashboard"],
)


def _tenant_root(workspace_id: str) -> str:
    return str(settings.STORAGE_ROOT / workspace_id)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    e5 = load_e5_analysis(_tenant_root(workspace.id))

    if not e5:
        return DashboardResponse(
            kpis=[],
            charts=[],
            alerts=[],
            data_freshness=None,
            periodo=None,
        )

    return DashboardResponse(
        kpis=build_kpis(e5),
        charts=build_charts(e5),
        alerts=build_alerts(e5),
        data_freshness=get_data_freshness(e5),
        periodo=get_periodo(e5),
    )


@router.get("/alerts", response_model=list[DashboardAlert])
async def get_alerts(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    e5 = load_e5_analysis(_tenant_root(workspace.id))

    if not e5:
        return []

    return build_alerts(e5)
