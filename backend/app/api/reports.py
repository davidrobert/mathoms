"""Reports router fino — list/get/data/pdf/tasks (A6e.4 · ADR-101 R15/R16 · ADR-129)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
    get_report_tasks as _get_report_tasks,
)
from backend.app.application.report import (
    list_consumo_pontuais as _list_consumo_pontuais,
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
from backend.app.repositories.config_blob_repository import ConfigBlobRepository
from backend.app.schemas.report import (
    ConsumoPontuaisResponse,
    ReportListResponse,
    ReportResponse,
    ReportTasksResponse,
)
from backend.app.services.access_audit import record_access_audit
from backend.app.services.audit import AuditAction
from backend.app.services.config_defaults import ConfigDefaultsLoader
from backend.app.services.transfer_detector_resolver import (
    resolve_internal_transfer_detector,
)

_defaults = ConfigDefaultsLoader()

router = APIRouter(
    prefix="/workspaces/{workspace_id}/reports",
    tags=["reports"],
)


@router.get(
    "",
    response_model=ReportListResponse,
    dependencies=[Depends(record_access_audit(AuditAction.report_read, "report"))],
)
async def list_reports(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    return await _list_reports(workspace.id, db=db)


_ANCHOR_DESC = (
    "Ancora ``date_to`` no fim do dataset (default: hoje UTC). "
    "Evita janela vazia em workspaces com dados antigos."
)


@router.get(
    "/consumo-pontuais",
    response_model=ConsumoPontuaisResponse,
    dependencies=[Depends(record_access_audit(AuditAction.report_read, "report"))],
)
async def list_consumo_pontuais(
    period: str = Query("3m", pattern=r"^(3m|6m|12m|ytd)$"),
    anchor_date: date | None = Query(None, description=_ANCHOR_DESC),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ConsumoPontuaisResponse:
    """Gastos pontuais ≥ R$2k no período, com transferências internas filtradas (card Consumo Consciente)."""
    detector = await resolve_internal_transfer_detector(
        workspace.id, repo=ConfigBlobRepository(db), defaults=_defaults
    )
    return await _list_consumo_pontuais(
        workspace.id, period=period, detector=detector, anchor_date=anchor_date, db=db
    )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    dependencies=[
        Depends(
            record_access_audit(AuditAction.report_read, "report", resource_id_param="report_id")
        )
    ],
)
async def get_report(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    return await _get_report(workspace.id, report_id, db=db)


@router.get(
    "/{report_id}/data",
    response_class=JSONResponse,
    dependencies=[
        Depends(
            record_access_audit(AuditAction.report_read, "report", resource_id_param="report_id")
        )
    ],
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
    dependencies=[
        Depends(
            record_access_audit(
                AuditAction.report_download, "report", resource_id_param="report_id"
            )
        )
    ],
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
