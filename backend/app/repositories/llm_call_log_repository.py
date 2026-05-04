"""``LLMCallLogRepository`` — escrita e agregações para FinOps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import LLMCallLog


@dataclass(frozen=True)
class WorkspaceSpendSummary:
    """Snapshot de gasto agregado de um workspace em janela arbitrária."""

    workspace_id: str
    period_start: datetime
    period_end: datetime
    call_count: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: Decimal
    unknown_cost_calls: int


def _aggregation_columns():
    """Tupla de agregações reusada por spend_in_period e by_workspace_summary."""
    return (
        func.count(LLMCallLog.id),
        func.coalesce(func.sum(LLMCallLog.tokens_in), 0),
        func.coalesce(func.sum(LLMCallLog.tokens_out), 0),
        func.coalesce(func.sum(LLMCallLog.cost_usd), Decimal("0")),
        func.coalesce(func.sum(case((LLMCallLog.cost_known.is_(False), 1), else_=0)), 0),
    )


def _row_to_summary(workspace_id: str, period_start, period_end, row) -> "WorkspaceSpendSummary":
    return WorkspaceSpendSummary(
        workspace_id=workspace_id,
        period_start=period_start,
        period_end=period_end,
        call_count=int(row[0] or 0),
        total_tokens_in=int(row[1] or 0),
        total_tokens_out=int(row[2] or 0),
        total_cost_usd=Decimal(row[3] or 0),
        unknown_cost_calls=int(row[4] or 0),
    )


class LLMCallLogRepository:
    """Persistência write-only por chamada + agregações de leitura."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, **fields) -> LLMCallLog:
        """Persiste 1 LLM call. Aceita kwargs do __init__ de LLMCallLog."""
        row = LLMCallLog(**fields)
        self._session.add(row)
        await self._session.flush()
        return row

    async def spend_in_period(
        self, *, workspace_id: str, since: datetime, until: Optional[datetime] = None
    ) -> WorkspaceSpendSummary:
        """Agrega cost/tokens/calls de um workspace na janela [since, until)."""
        end = until or datetime.now(timezone.utc)
        stmt = select(*_aggregation_columns()).where(
            LLMCallLog.workspace_id == workspace_id,
            LLMCallLog.created_at >= since,
            LLMCallLog.created_at < end,
        )
        row = (await self._session.execute(stmt)).one()
        return _row_to_summary(workspace_id, since, end, row)

    async def by_workspace_summary(
        self, *, since: datetime, until: Optional[datetime] = None
    ) -> list[WorkspaceSpendSummary]:
        """Agrega por workspace na janela — ordenado por gasto desc."""
        end = until or datetime.now(timezone.utc)
        stmt = (
            select(LLMCallLog.workspace_id, *_aggregation_columns())
            .where(LLMCallLog.created_at >= since, LLMCallLog.created_at < end)
            .group_by(LLMCallLog.workspace_id)
            .order_by(func.sum(LLMCallLog.cost_usd).desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [_row_to_summary(row[0], since, end, row[1:]) for row in rows]
