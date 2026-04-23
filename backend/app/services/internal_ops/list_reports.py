"""Lista read-only de relatórios para o console interno (7F.14 · ADR-116)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.report import Report
from backend.app.models.workspace import Workspace


@dataclass(frozen=True)
class ReportSummary:
    id: str
    workspace_id: str
    title: str
    period: str | None
    created_at: datetime
    size_bytes: int | None


@dataclass(frozen=True)
class ListReportsFilter:
    user_id: str | None = None
    workspace_id: str | None = None
    limit: int = 100


async def list_reports(db: AsyncSession, *, filter: ListReportsFilter) -> list[ReportSummary]:
    stmt = select(Report).order_by(Report.created_at.desc())
    if filter.workspace_id:
        stmt = stmt.where(Report.workspace_id == filter.workspace_id)
    elif filter.user_id:
        stmt = stmt.join(Workspace, Report.workspace_id == Workspace.id).where(
            Workspace.owner_id == filter.user_id
        )
    stmt = stmt.limit(max(1, min(filter.limit, 500)))
    rows = (await db.execute(stmt)).scalars().all()
    return [
        ReportSummary(
            id=r.id,
            workspace_id=r.workspace_id,
            title=r.title,
            period=r.period,
            created_at=r.created_at,
            size_bytes=r.size_bytes,
        )
        for r in rows
    ]
