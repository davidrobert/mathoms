"""Report publications API — ADR-186 (mês fechado imutável)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.report_publication import (
    ReportPublicationCreate,
    ReportPublicationListResponse,
    ReportPublicationResponse,
    to_response,
)
from backend.app.services import report_publication as report_publication_service

router = APIRouter(
    prefix="/workspaces/{workspace_id}/reports",
    tags=["report-publications"],
)


def _actor_id(user: User) -> str:
    return f"user:{user.id}"


@router.post(
    "/{period_yyyymm}/publish",
    response_model=ReportPublicationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def publish_report(
    period_yyyymm: str,
    payload: ReportPublicationCreate,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportPublicationResponse:
    publication = await report_publication_service.publish_month(
        workspace.id,
        period_yyyymm,
        payload.artifact_id,
        actor=_actor_id(user),
        db=db,
    )
    await db.commit()
    return to_response(publication)


@router.delete(
    "/{period_yyyymm}/publish",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_role)],
)
async def unpublish_report(
    period_yyyymm: str,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await report_publication_service.unpublish_month(
        workspace.id,
        period_yyyymm,
        actor=_actor_id(user),
        db=db,
    )
    await db.commit()
    return None


@router.get(
    "/publications",
    response_model=ReportPublicationListResponse,
)
async def list_publications(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ReportPublicationListResponse:
    publications = await report_publication_service.list_publications(workspace.id, db=db)
    return ReportPublicationListResponse(items=[to_response(p) for p in publications])


@router.get(
    "/{period_yyyymm}/publication",
    response_model=ReportPublicationResponse | None,
)
async def get_active_publication(
    period_yyyymm: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ReportPublicationResponse | None:
    """Publicação viva do (workspace, period), ou ``null`` se mês está aberto."""
    publication = await report_publication_service.get_active_publication(
        workspace.id, period_yyyymm, db=db
    )
    if publication is None:
        return None
    return to_response(publication)
