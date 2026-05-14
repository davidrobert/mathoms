"""Admin endpoint — telemetria de campos faltantes do parecer (ADR-206 M4). Top-N para dashboard semanal do `product-manager`."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.internal_ops_auth import (
    InternalOpsPrincipal,
    require_internal_operator,
)
from backend.app.repositories.planner_field_request_repository import (
    PlannerFieldRequestRepository,
)
from backend.app.schemas.admin import (
    PlannerFieldRequestTopItem,
    PlannerFieldRequestTopResponse,
)

router = APIRouter()


@router.get(
    "/planner-review/field-requests/top",
    response_model=PlannerFieldRequestTopResponse,
)
async def planner_field_requests_top(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> PlannerFieldRequestTopResponse:
    """Top-N campos pedidos pelo LLM em N dias — input para tunning v2 do manifest (ADR-206)."""
    aggregates = await PlannerFieldRequestRepository(db).top_requested_fields(
        days=days, limit=limit
    )
    items = [
        PlannerFieldRequestTopItem(
            field_path=a.field_path,
            frequency=a.frequency,
            workspaces_count=a.workspaces_count,
            last_requested_at=a.last_requested_at.isoformat(),
        )
        for a in aggregates
    ]
    return PlannerFieldRequestTopResponse(days=days, limit=limit, items=items)
