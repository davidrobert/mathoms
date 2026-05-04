"""Admin routes — métricas + audit + LLM cost (FinOps)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.internal_ops_auth import (
    InternalOpsPrincipal,
    require_internal_operator,
)
from backend.app.models import Workspace
from backend.app.repositories.llm_call_log_repository import LLMCallLogRepository
from backend.app.schemas.admin import (
    AuditEntryDTO,
    AuditListResponse,
    LLMSpendByWorkspaceResponse,
    MetricsResponse,
    WorkspaceLLMSpendDTO,
)
from backend.app.services.internal_ops import get_metrics
from backend.app.services.internal_ops.audit import read_audit

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def metrics(
    period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> MetricsResponse:
    snap = await get_metrics(db, period_days=period_days)
    return MetricsResponse(
        users_total=snap.users_total,
        users_active=snap.users_active,
        workspaces_total=snap.workspaces_total,
        documents_total=snap.documents_total,
        documents_needs_review=snap.documents_needs_review,
        storage_bytes_total=snap.storage_bytes_total,
        pipeline_runs_total=snap.pipeline_runs_total,
        pipeline_runs_last_period=snap.pipeline_runs_last_period,
        documents_uploaded_last_period=snap.documents_uploaded_last_period,
        new_users_last_period=snap.new_users_last_period,
        period_days=snap.period_days,
        generated_at=snap.generated_at,
    )


@router.get("/audit", response_model=AuditListResponse)
async def audit(
    limit: int = Query(default=200, ge=1, le=2000),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> AuditListResponse:
    entries = read_audit(limit=limit)
    return AuditListResponse(entries=[AuditEntryDTO(**e) for e in entries])


async def _lookup_ws_name_budget(
    db: AsyncSession, ws_ids: list[str]
) -> dict[str, tuple[str, Decimal]]:
    """Resolve {workspace_id: (name, monthly_llm_budget_usd)} numa única query."""
    if not ws_ids:
        return {}
    stmt = select(Workspace.id, Workspace.name, Workspace.monthly_llm_budget_usd).where(
        Workspace.id.in_(ws_ids)
    )
    return {r[0]: (r[1], r[2]) for r in (await db.execute(stmt)).all()}


def _summary_to_dto(summary, name_budget: dict) -> WorkspaceLLMSpendDTO:
    name, budget = name_budget.get(summary.workspace_id, (None, Decimal("5.00")))
    pct = float(summary.total_cost_usd / budget) if budget and budget > 0 else 0.0
    return WorkspaceLLMSpendDTO(
        workspace_id=summary.workspace_id,
        workspace_name=name,
        monthly_budget_usd=str(budget),
        period_start=summary.period_start.isoformat(),
        period_end=summary.period_end.isoformat(),
        call_count=summary.call_count,
        total_tokens_in=summary.total_tokens_in,
        total_tokens_out=summary.total_tokens_out,
        total_cost_usd=str(summary.total_cost_usd),
        unknown_cost_calls=summary.unknown_cost_calls,
        pct_of_budget=pct,
        over_budget=pct >= 1.0,
    )


@router.get("/llm-cost-by-workspace", response_model=LLMSpendByWorkspaceResponse)
async def llm_cost_by_workspace(
    period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> LLMSpendByWorkspaceResponse:
    """Gasto LLM por workspace em USD na janela. Inclui pct_of_budget para alarme."""
    end = datetime.now(timezone.utc)
    since = end - timedelta(days=period_days)
    summaries = await LLMCallLogRepository(db).by_workspace_summary(since=since, until=end)
    name_budget = await _lookup_ws_name_budget(db, [s.workspace_id for s in summaries])
    items = [_summary_to_dto(s, name_budget) for s in summaries]
    return LLMSpendByWorkspaceResponse(
        period_days=period_days,
        period_start=since.isoformat(),
        period_end=end.isoformat(),
        items=items,
    )
