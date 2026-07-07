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
    LLMBudgetMonthResponse,
    LLMSpendByWorkspaceResponse,
    MetricsResponse,
    WorkspaceLLMBudgetMonthDTO,
    WorkspaceLLMSpendDTO,
)
from backend.app.services.internal_ops import get_metrics
from backend.app.services.internal_ops.audit import read_audit
from backend.app.services.llm_budget_service import (
    HARD_STOP_RATIO,
    WARN_RATIO,
    current_month_window,
)

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


def _budget_status(spent: Decimal, cap: Decimal | None) -> tuple[str, float | None]:
    """Classificação com os MESMOS ratios/janela do hard-stop (ADR-173)."""
    if cap is None or cap <= 0:
        return "uncapped", None
    pct = float(spent / cap)
    if spent >= cap * HARD_STOP_RATIO:
        return "hard_stop", pct
    if spent >= cap * WARN_RATIO:
        return "warn", pct
    return "ok", pct


def _month_dto(ws_id: str, name: str | None, cap, summary) -> WorkspaceLLMBudgetMonthDTO:
    cap_dec = None if cap is None else Decimal(cap)
    spent = (summary.total_cost_usd if summary else Decimal("0")).quantize(Decimal("0.01"))
    budget_status, pct = _budget_status(spent, cap_dec)
    return WorkspaceLLMBudgetMonthDTO(
        workspace_id=ws_id,
        workspace_name=name,
        cap_usd=None if cap_dec is None else str(cap_dec),
        spent_month_usd=str(spent),
        pct_of_cap=pct,
        status=budget_status,
        call_count=summary.call_count if summary else 0,
        unknown_cost_calls=summary.unknown_cost_calls if summary else 0,
    )


async def _month_items(db: AsyncSession, month_start, now) -> list[WorkspaceLLMBudgetMonthDTO]:
    summaries = await LLMCallLogRepository(db).by_workspace_summary(since=month_start, until=now)
    by_ws = {s.workspace_id: s for s in summaries}
    rows = (
        await db.execute(select(Workspace.id, Workspace.name, Workspace.monthly_llm_budget_usd))
    ).all()
    items = [_month_dto(r[0], r[1], r[2], by_ws.get(r[0])) for r in rows]
    items.sort(key=lambda i: (i.pct_of_cap is None, -(i.pct_of_cap or 0.0), i.workspace_id))
    return items


@router.get("/llm-budget-by-workspace", response_model=LLMBudgetMonthResponse)
async def llm_budget_by_workspace(
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> LLMBudgetMonthResponse:
    """Cap + gasto do mês-calendário UTC por workspace — base do editor de budget (A30.l1)."""
    month_start, _month_key = current_month_window()
    now = datetime.now(timezone.utc)
    return LLMBudgetMonthResponse(
        month=month_start.strftime("%Y-%m"),
        period_start=month_start.isoformat(),
        period_end=now.isoformat(),
        warn_ratio=float(WARN_RATIO),
        hard_stop_ratio=float(HARD_STOP_RATIO),
        items=await _month_items(db, month_start, now),
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
