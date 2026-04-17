"""Report endpoints — list and serve HTML reports (tenant-scoped, ADR-072)."""

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.report import Report
from backend.app.schemas.report import ReportResponse, ReportListResponse
from backend.app.services import report_tasks_snapshot_service, task_service
from backend.app.schemas.task import TaskFilters, TaskResponse

router = APIRouter(
    prefix="/workspaces/{workspace_id}/reports",
    tags=["reports"],
)


def _serialize_report(report: Report) -> ReportResponse:
    """Build ReportResponse with `has_analysis_data` derived from the model (F9)."""
    return ReportResponse(
        id=report.id,
        workspace_id=report.workspace_id,
        title=report.title,
        period=report.period,
        size_bytes=report.size_bytes,
        score=report.score,
        patrimonio_liquido=report.patrimonio_liquido,
        created_at=report.created_at,
        pipeline_run_id=report.pipeline_run_id,
        has_analysis_data=bool(report.analysis_json_path),
    )


@router.get("", response_model=ReportListResponse)
async def list_reports(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .where(Report.workspace_id == workspace.id)
        .order_by(Report.created_at.desc())
    )
    reports = list(result.scalars().all())
    return ReportListResponse(
        reports=[_serialize_report(r) for r in reports],
        total=len(reports),
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == workspace.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return _serialize_report(report)


@router.get("/{report_id}/html", response_class=HTMLResponse)
async def get_report_html(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == workspace.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    html_path = Path(report.html_path)
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo HTML não encontrado no disco")

    html_content = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)


def _sanitize_filename(raw: str) -> str:
    """Whitelist [A-Za-z0-9._-] para impedir injeção em Content-Disposition."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", raw).strip("._")
    return cleaned or "relatorio.html"


@router.get("/{report_id}/download.html")
async def download_report_html(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Download do relatório HTML standalone (F9 · F1.5).

    Endpoint substitui GET /{id}/html quando o objetivo é preservar o artefato
    (ex: compartilhar com contador, anexo de e-mail, backup). O HTML standalone
    continua sendo gerado pelo E6 e mora em `report.html_path`.
    """
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == workspace.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    html_path = Path(report.html_path)
    if not html_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Arquivo HTML não encontrado no disco",
        )

    filename = _sanitize_filename(html_path.name)
    return FileResponse(
        html_path,
        media_type="text/html; charset=utf-8",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/data")
async def get_report_data(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Serve o snapshot E5 JSON do relatório para o render nativo React (F9 · F0.4).

    ADR-076: o render nativo consome o JSON estruturado ao invés de parsear
    o HTML do iframe. Relatórios pré-F9 (sem analysis_json_path) retornam 404.
    """
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == workspace.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    if not report.analysis_json_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Este relatório não tem JSON de análise disponível "
                "(gerado antes do F9). Use /html ou /download.html."
            ),
        )

    json_path = Path(report.analysis_json_path)
    if not json_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo JSON de análise não encontrado no disco",
        )

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JSON de análise corrompido: {exc}",
        )

    return JSONResponse(content=payload)


@router.get("/{report_id}/download.pdf")
async def download_report_pdf(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gera PDF server-side via Playwright (F9 · ADR-076 · F4.2).

    Renderiza a rota nativa React (/reports/{id}) em headless Chromium
    e retorna o PDF como download. Recharts SVG imprime nativamente
    (sem fallback Canvas→PNG).
    """
    from backend.app.core.config import settings
    from backend.app.core.security import create_access_token
    from backend.app.services.pdf_renderer import render_pdf

    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.workspace_id == workspace.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    # Gera token efêmero (60s) para que Playwright possa autenticar
    # na rota do frontend — não reusa o token do usuário (poderia expirar
    # durante o render).
    from datetime import timedelta

    ephemeral_token = create_access_token(
        current_user.id, expires_delta=timedelta(minutes=1)
    )

    frontend_base = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    report_url = f"{frontend_base}/reports/{report_id}?print=1"

    try:
        pdf_bytes = await render_pdf(
            report_url=report_url,
            bearer_token=ephemeral_token,
            timeout_ms=30_000,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao gerar PDF: {exc}",
        )

    filename = _sanitize_filename(
        f"relatorio-{report_id[:8]}.pdf"
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{report_id}/tasks")
async def get_report_tasks(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Tasks do relatório (ADR-074 §F8.3 — snapshot imutável).

    - Se `tasks_snapshot_json` está populado: retorna a foto do momento
      da geração (imutável).
    - Se não (relatórios pré-F8.3): fallback para estado live do backlog
      no workspace, marcado com `is_live_fallback: true` para a UI
      mostrar aviso.
    """
    snapshot = await report_tasks_snapshot_service.get_report_snapshot(
        workspace.id, report_id, db=db
    )
    if snapshot is not None:
        return JSONResponse(content={"is_live_fallback": False, **snapshot})

    # Fallback: estado live (para relatórios pré-F8.3 OU geração inicial sem snapshot)
    # Valida que o relatório existe no workspace antes de vazar tasks
    result = await db.execute(
        select(Report).where(
            Report.id == report_id, Report.workspace_id == workspace.id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Relatório não encontrado"
        )

    live_tasks = await task_service.list_tasks(
        workspace.id, TaskFilters(include_done=True, include_cancelled=True), db=db
    )
    return JSONResponse(
        content={
            "is_live_fallback": True,
            "version": 1,
            "captured_at": None,
            "total": len(live_tasks),
            "counts_by_status": {},
            "counts_by_priority": {},
            "tasks": [
                TaskResponse.model_validate(t).model_dump(mode="json")
                for t in live_tasks
            ],
        }
    )
