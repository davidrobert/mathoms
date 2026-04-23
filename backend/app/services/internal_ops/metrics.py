"""Métricas básicas para o dashboard do console interno (7F.13 · ADR-116).

MVP: contagens (users, workspaces, documents, runs) + volume total de
storage. Sem cache in-memory (ADR-111). Sem agregações monetárias no MVP;
quando entrarem serão `Decimal`/`Money` (ADR-090).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.models.pipeline_run import PipelineRun
from backend.app.models.user import User
from backend.app.models.workspace import Workspace


@dataclass(frozen=True)
class MetricsSnapshot:
    users_total: int
    users_active: int
    workspaces_total: int
    documents_total: int
    documents_needs_review: int
    storage_bytes_total: int
    pipeline_runs_total: int
    pipeline_runs_last_period: int
    documents_uploaded_last_period: int
    new_users_last_period: int
    period_days: int
    generated_at: str


async def get_metrics(db: AsyncSession, *, period_days: int = 30) -> MetricsSnapshot:
    users_total = int((await db.execute(select(func.count()).select_from(User))).scalar_one() or 0)
    users_active = int(
        (
            await db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))
        ).scalar_one()
        or 0
    )
    workspaces_total = int(
        (await db.execute(select(func.count()).select_from(Workspace))).scalar_one() or 0
    )
    documents_total = int(
        (await db.execute(select(func.count()).select_from(Document))).scalar_one() or 0
    )
    documents_needs_review = int(
        (
            await db.execute(
                select(func.count()).select_from(Document).where(Document.needs_review.is_(True))
            )
        ).scalar_one()
        or 0
    )
    storage_bytes_total = int(
        (
            await db.execute(select(func.coalesce(func.sum(Document.file_size_bytes), 0)))
        ).scalar_one()
        or 0
    )
    pipeline_runs_total = int(
        (await db.execute(select(func.count()).select_from(PipelineRun))).scalar_one() or 0
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
    pipeline_runs_last_period = int(
        (
            await db.execute(
                select(func.count())
                .select_from(PipelineRun)
                .where(PipelineRun.started_at >= cutoff)
            )
        ).scalar_one()
        or 0
    )
    documents_uploaded_last_period = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Document)
                .where(Document.uploaded_at >= cutoff)
            )
        ).scalar_one()
        or 0
    )
    new_users_last_period = int(
        (
            await db.execute(
                select(func.count()).select_from(User).where(User.created_at >= cutoff)
            )
        ).scalar_one()
        or 0
    )
    return MetricsSnapshot(
        users_total=users_total,
        users_active=users_active,
        workspaces_total=workspaces_total,
        documents_total=documents_total,
        documents_needs_review=documents_needs_review,
        storage_bytes_total=storage_bytes_total,
        pipeline_runs_total=pipeline_runs_total,
        pipeline_runs_last_period=pipeline_runs_last_period,
        documents_uploaded_last_period=documents_uploaded_last_period,
        new_users_last_period=new_users_last_period,
        period_days=period_days,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
