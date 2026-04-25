"""Lista read-only de relatórios para o console interno (7F.14 · ADR-116)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.report import Report
from backend.app.models.user import User
from backend.app.models.workspace import Workspace


@dataclass(frozen=True)
class ReportSummary:
    id: str
    workspace_id: str
    title: str
    period: str | None
    created_at: datetime
    owner_email: str | None
    workspace_name: str | None


@dataclass(frozen=True)
class ListReportsFilter:
    user_id: str | None = None
    workspace_id: str | None = None
    limit: int = 100
    offset: int = 0


async def list_reports(
    db: AsyncSession, *, filter: ListReportsFilter
) -> tuple[list[ReportSummary], int]:
    """Retorna (page, total). Total serve UI para calcular #páginas."""
    # JOIN explícito com Workspace+User para trazer owner_email e workspace_name
    # numa query só (evita N+1). outerjoin porque pipeline_run_id é FK nullable e
    # precisamos ser defensivos caso workspace/user seja deletado no futuro.
    base = (
        select(Report, Workspace.name, User.email)
        .outerjoin(Workspace, Report.workspace_id == Workspace.id)
        .outerjoin(User, Workspace.owner_id == User.id)
    )
    if filter.workspace_id:
        base = base.where(Report.workspace_id == filter.workspace_id)
    elif filter.user_id:
        base = base.where(Workspace.owner_id == filter.user_id)

    total = int(
        (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0
    )
    limit = max(1, min(filter.limit, 500))
    offset = max(0, filter.offset)
    stmt = base.order_by(Report.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).all()
    summaries = [
        ReportSummary(
            id=r.id,
            workspace_id=r.workspace_id,
            title=r.title,
            period=r.period,
            created_at=r.created_at,
            owner_email=email,
            workspace_name=ws_name,
        )
        for r, ws_name, email in rows
    ]
    return summaries, total
