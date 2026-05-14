"""PlannerFieldRequestRepository — telemetria M4 (ADR-206). Queries agregadas para dashboard semanal top-10; insert idempotente por (review_id, field_path)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.planner_field_request import PlannerFieldRequest


@dataclass(frozen=True)
class FieldRequestAggregate:
    """Top-N agregação para dashboard ADR-206 §D3."""

    field_path: str
    frequency: int
    workspaces_count: int
    last_requested_at: datetime


def _build_top_stmt(*, since: datetime, limit: int):
    """Statement SQL para top-N agregação por field_path."""
    return (
        select(
            PlannerFieldRequest.field_path,
            func.count().label("frequency"),
            func.count(func.distinct(PlannerFieldRequest.workspace_id)).label("ws_count"),
            func.max(PlannerFieldRequest.created_at).label("last_at"),
        )
        .where(PlannerFieldRequest.created_at >= since)
        .group_by(PlannerFieldRequest.field_path)
        .order_by(func.count().desc())
        .limit(limit)
    )


def _row_to_aggregate(row) -> FieldRequestAggregate:
    """Tupla SQL → dataclass tipada."""
    return FieldRequestAggregate(
        field_path=row[0],
        frequency=int(row[1]),
        workspaces_count=int(row[2]),
        last_requested_at=row[3],
    )


class PlannerFieldRequestRepository:
    """Single Responsibility: persistência + queries agregadas de ``PlannerFieldRequest``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def top_requested_fields(
        self, *, days: int = 30, limit: int = 10
    ) -> list[FieldRequestAggregate]:
        """Top-N paths mais pedidos na janela; usado por dashboard admin (ADR-206 §D4)."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (await self._session.execute(_build_top_stmt(since=since, limit=limit))).all()
        return [_row_to_aggregate(r) for r in rows]

    async def list_for_review(self, planner_review_id: str) -> list[PlannerFieldRequest]:
        """Lista rows de um parecer específico — drill-down qualitativo."""
        result = await self._session.execute(
            select(PlannerFieldRequest)
            .where(PlannerFieldRequest.planner_review_id == planner_review_id)
            .order_by(PlannerFieldRequest.field_path)
        )
        return list(result.scalars().all())


__all__ = ["FieldRequestAggregate", "PlannerFieldRequestRepository"]
