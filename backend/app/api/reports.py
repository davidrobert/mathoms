"""Reports router fino — list/get/html/pdf/data/tasks (A6e.4 · ADR-101 R15/R16)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.report import (
    download_report_html as _download_report_html,
)
from backend.app.application.report import (
    download_report_pdf as _download_report_pdf,
)
from backend.app.application.report import (
    get_report as _get_report,
)
from backend.app.application.report import (
    get_report_data as _get_report_data,
)
from backend.app.application.report import (
    get_report_html as _get_report_html,
)
from backend.app.application.report import (
    get_report_tasks as _get_report_tasks,
)
from backend.app.application.report import (
    list_reports as _list_reports,
)
from backend.app.application.report._common import (
    sanitize_filename as _sanitize_filename,  # noqa: F401  # re-export para test histórico
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.report import (
    ReportListResponse,
    ReportResponse,
    ReportTasksResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/reports",
    tags=["reports"],
)


@router.get("", response_model=ReportListResponse)
async def list_reports(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    return await _list_reports(workspace.id, db=db)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    return await _get_report(workspace.id, report_id, db=db)


@router.get("/{report_id}/html", response_class=HTMLResponse)
async def get_report_html(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    return await _get_report_html(workspace.id, report_id, db=db)


@router.get("/{report_id}/download.html", response_class=FileResponse)
async def download_report_html(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    return await _download_report_html(workspace.id, report_id, db=db)


@router.get(
    "/{report_id}/data",
    response_class=JSONResponse,
    responses={
        200: {
            "description": (
                "Snapshot E5 JSON (24+ chaves top-level). Schema dinâmico — "
                "consumidores devem usar esquema frouxo (``map[string]any`` / "
                "``Record<string, unknown>``). Campos injetados: "
                "``_report_lineage``, ``goals.premissas_snapshot``."
            ),
            "content": {"application/json": {"schema": {"type": "object"}}},
        },
    },
)
async def get_report_data(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    return await _get_report_data(workspace.id, report_id, db=db)


@router.get(
    "/{report_id}/download.pdf",
    response_class=Response,
    responses={
        200: {
            "description": "PDF binary (application/pdf).",
            "content": {"application/pdf": {}},
        },
    },
)
async def download_report_pdf(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    return await _download_report_pdf(workspace.id, report_id, user=current_user, db=db)


@router.get("/{report_id}/tasks", response_model=ReportTasksResponse)
async def get_report_tasks(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    return await _get_report_tasks(workspace.id, report_id, db=db)
