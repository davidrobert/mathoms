"""Use cases: HTML inline + HTML download do relatório (F9)."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import NotFoundError
from backend.app.application.report._common import fetch_report, sanitize_filename


async def get_report_html(workspace_id: str, report_id: str, *, db: AsyncSession) -> HTMLResponse:
    report = await fetch_report(workspace_id, report_id, db=db)
    html_path = Path(report.html_path)
    if not html_path.exists():
        raise NotFoundError("Arquivo HTML não encontrado no disco")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


async def download_report_html(
    workspace_id: str, report_id: str, *, db: AsyncSession
) -> FileResponse:
    report = await fetch_report(workspace_id, report_id, db=db)
    html_path = Path(report.html_path)
    if not html_path.exists():
        raise NotFoundError("Arquivo HTML não encontrado no disco")
    filename = sanitize_filename(html_path.name)
    return FileResponse(
        html_path,
        media_type="text/html; charset=utf-8",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
