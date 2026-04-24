"""Report collaboration — Notes (T6) + Kanban (T3) endpoints.

ADR-123 · Fase 6.5. Endpoints sob ``/workspaces/{workspace_id}/reports/
{report_id}/{notes|kanban[/item_id]}``.

Padrão thin-router: queries diretas (sem use case) — CRUD simples sobre
2 tabelas, sem regras de domínio complexas além de validação de
ownership (report pertence ao workspace).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models import (
    KanbanItem,
    Report,
    ReportNotes,
    User,
    Workspace,
)
from backend.app.schemas.report_collab import (
    KanbanItemCreate,
    KanbanItemListResponse,
    KanbanItemRead,
    KanbanItemUpdate,
    ReportNotesRead,
    ReportNotesWrite,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/reports/{report_id}",
    tags=["report-collab"],
)


async def _ensure_report_in_workspace(
    db: AsyncSession, workspace: Workspace, report_id: str
) -> None:
    """Valida que o report pertence ao workspace. 404 caso contrário."""
    stmt = select(Report.id).where(Report.id == report_id, Report.workspace_id == workspace.id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Report not found")


# ═════════════════════════════════════════════════════════════════════
# Notes (T6) — 1:1 com report
# ═════════════════════════════════════════════════════════════════════


@router.get("/notes", response_model=ReportNotesRead | None)
async def get_notes(
    report_id: Annotated[str, Path()],
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ReportNotesRead | None:
    """Retorna as notas do relatório ou None (204-ish) quando vazio."""
    await _ensure_report_in_workspace(db, workspace, report_id)
    stmt = select(ReportNotes).where(
        ReportNotes.workspace_id == workspace.id,
        ReportNotes.report_id == report_id,
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return ReportNotesRead.model_validate(row)


@router.put("/notes", response_model=ReportNotesRead)
async def put_notes(
    report_id: Annotated[str, Path()],
    body: ReportNotesWrite,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportNotesRead:
    """Upsert idempotente — cria se não existe, atualiza content + author."""
    await _ensure_report_in_workspace(db, workspace, report_id)
    stmt = select(ReportNotes).where(
        ReportNotes.workspace_id == workspace.id,
        ReportNotes.report_id == report_id,
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        row = ReportNotes(
            id=str(uuid.uuid4()),
            workspace_id=workspace.id,
            report_id=report_id,
            author_user_id=user.id,
            content=body.content,
        )
        db.add(row)
    else:
        row.content = body.content
        row.author_user_id = user.id
    await db.commit()
    await db.refresh(row)
    return ReportNotesRead.model_validate(row)


# ═════════════════════════════════════════════════════════════════════
# Kanban (T3) — 1:N com report
# ═════════════════════════════════════════════════════════════════════


@router.get("/kanban", response_model=KanbanItemListResponse)
async def list_kanban(
    report_id: Annotated[str, Path()],
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> KanbanItemListResponse:
    """Lista todos items do Kanban deste relatório, ordenados por
    (coluna, ordem, created_at). Frontend decide como agrupar."""
    await _ensure_report_in_workspace(db, workspace, report_id)
    stmt = (
        select(KanbanItem)
        .where(
            KanbanItem.workspace_id == workspace.id,
            KanbanItem.report_id == report_id,
        )
        .order_by(KanbanItem.coluna, KanbanItem.ordem, KanbanItem.created_at)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return KanbanItemListResponse(items=[KanbanItemRead.model_validate(r) for r in rows])


@router.post("/kanban", response_model=KanbanItemRead, status_code=status.HTTP_201_CREATED)
async def create_kanban_item(
    report_id: Annotated[str, Path()],
    body: KanbanItemCreate,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KanbanItemRead:
    await _ensure_report_in_workspace(db, workspace, report_id)
    row = KanbanItem(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        report_id=report_id,
        titulo=body.titulo,
        coluna=body.coluna,
        prioridade=body.prioridade,
        prazo=body.prazo,
        categoria=body.categoria,
        essencial=body.essencial,
        ordem=body.ordem,
        created_by=user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return KanbanItemRead.model_validate(row)


@router.patch("/kanban/{item_id}", response_model=KanbanItemRead)
async def update_kanban_item(
    report_id: Annotated[str, Path()],
    item_id: Annotated[str, Path()],
    body: KanbanItemUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> KanbanItemRead:
    await _ensure_report_in_workspace(db, workspace, report_id)
    stmt = select(KanbanItem).where(
        KanbanItem.id == item_id,
        KanbanItem.workspace_id == workspace.id,
        KanbanItem.report_id == report_id,
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Kanban item not found")
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return KanbanItemRead.model_validate(row)


@router.delete("/kanban/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kanban_item(
    report_id: Annotated[str, Path()],
    item_id: Annotated[str, Path()],
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _ensure_report_in_workspace(db, workspace, report_id)
    stmt = select(KanbanItem).where(
        KanbanItem.id == item_id,
        KanbanItem.workspace_id == workspace.id,
        KanbanItem.report_id == report_id,
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Kanban item not found")
    await db.delete(row)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
