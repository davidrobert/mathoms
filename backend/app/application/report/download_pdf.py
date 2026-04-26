"""Use case: render server-side de PDF via Playwright (ADR-076 · F9)."""

from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.report._common import (
    compose_pdf_filename,
    fetch_report,
    sanitize_filename,
)
from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.pdf_renderer import render_pdf


async def download_report_pdf(
    workspace_id: str,
    report_id: str,
    *,
    user: User,
    db: AsyncSession,
) -> Response:
    report = await fetch_report(workspace_id, report_id, db=db)
    workspace = await db.get(Workspace, workspace_id)
    surname = workspace.family_surname if workspace is not None else None

    # Token efêmero (60s) para Playwright autenticar na rota do frontend.
    ephemeral_token = create_access_token(user.id, expires_delta=timedelta(minutes=1))
    frontend_base = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    report_url = f"{frontend_base}/reports/{report_id}?print=1"

    pdf_bytes = await _render_or_raise(report_url, ephemeral_token)

    filename = sanitize_filename(compose_pdf_filename(surname, report.period, report.created_at))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _render_or_raise(report_url: str, bearer_token: str) -> bytes:
    try:
        return await render_pdf(report_url=report_url, bearer_token=bearer_token, timeout_ms=30_000)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao gerar PDF: {exc}",
        ) from exc
