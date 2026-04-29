"""Admin routes — relatórios (listing read-only + purge bulk)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.internal_ops_auth import (
    InternalOpsPrincipal,
    require_internal_operator,
)
from backend.app.schemas.admin import (
    AdminReportListResponse,
    PurgeReportsRequest,
    PurgeReportsResponse,
    ReportSummaryDTO,
    ScopeContextDTO,
)
from backend.app.services.internal_ops import (
    ListReportsFilter,
    PurgeScope,
    list_reports,
    purge_reports,
)

router = APIRouter(prefix="/reports")


def _to_summary_dto(r) -> ReportSummaryDTO:
    return ReportSummaryDTO(
        id=r.id,
        workspace_id=r.workspace_id,
        title=r.title,
        period=r.period,
        created_at=r.created_at,
        owner_email=r.owner_email,
        workspace_name=r.workspace_name,
    )


def _to_purge_response(details: dict) -> PurgeReportsResponse:
    ctx_raw = details.get("scope_context") or {}
    return PurgeReportsResponse(
        preview=details["preview"],
        count=details["count"],
        ids=list(details["ids"]),
        artifacts_to_remove=details.get("artifacts_to_remove", 0),
        artifacts_removed=details.get("artifacts_removed"),
        scope_context=ScopeContextDTO(
            owner_email=ctx_raw.get("owner_email"),
            workspace_names=list(ctx_raw.get("workspace_names") or []),
        ),
    )


@router.get("", response_model=AdminReportListResponse)
async def list_(
    user_id: str | None = Query(default=None),
    workspace_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: InternalOpsPrincipal = Depends(require_internal_operator),
) -> AdminReportListResponse:
    reports, total = await list_reports(
        db,
        filter=ListReportsFilter(
            user_id=user_id, workspace_id=workspace_id, limit=limit, offset=offset
        ),
    )
    return AdminReportListResponse(
        reports=[_to_summary_dto(r) for r in reports],
        total=total,
    )


@router.post("/purge", response_model=PurgeReportsResponse)
async def purge(
    body: PurgeReportsRequest,
    db: AsyncSession = Depends(get_db),
    principal: InternalOpsPrincipal = Depends(require_internal_operator),
) -> PurgeReportsResponse:
    if not body.user_id and not body.workspace_id:
        raise HTTPException(status_code=422, detail="scope_required")
    result = await purge_reports(
        db,
        scope=PurgeScope(user_id=body.user_id, workspace_id=body.workspace_id),
        actor=principal.actor,
        preview=body.preview,
    )
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)
    await db.commit()
    return _to_purge_response(result.details)
