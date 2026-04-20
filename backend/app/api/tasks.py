"""Tasks API — F8.2 (ADR-074).

Endpoints no padrão F8+: prefix `/api/workspaces/{workspace_id}/...`
usando `get_current_workspace`. Tenancy lint (ADR-072) passa porque
todas as queries em task_service filtram por `workspace_id`.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.schemas.task import (
    ScanDeadlinesResponse,
    TaskAttachmentListResponse,
    TaskAttachmentResponse,
    TaskCreate,
    TaskFilters,
    TaskListResponse,
    TaskProgress,
    TaskResponse,
    TaskStatusTransition,
    TaskSuggestionApprove,
    TaskSuggestionCreate,
    TaskSuggestionListResponse,
    TaskSuggestionReject,
    TaskSuggestionResponse,
    TaskUpdate,
)
from backend.app.services import (
    task_attachment_service,
    task_notification_service,
    task_progress_service,
    task_service,
    task_suggestion_service,
)
from backend.app.services.storage import StorageService

router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["tasks"],
)


# ═══════════════════════════════════════════════════════════════════════
# Tasks
# ═══════════════════════════════════════════════════════════════════════


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = None,  # evita conflito com import `status`
    priority: Optional[str] = None,
    category: Optional[str] = None,
    deadline_before: Optional[date] = None,
    deadline_after: Optional[date] = None,
    assigned_to: Optional[str] = None,
    related_goal_id: Optional[str] = None,
    include_done: bool = False,
    include_cancelled: bool = False,
):
    filters = TaskFilters(
        status=status_filter,  # type: ignore[arg-type]
        priority=priority,  # type: ignore[arg-type]
        category=category,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
        assigned_to=assigned_to,
        related_goal_id=related_goal_id,
        include_done=include_done,
        include_cancelled=include_cancelled,
    )
    tasks = await task_service.list_tasks(workspace.id, filters, db=db)
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
    )


@router.get("/tasks/upcoming", response_model=TaskListResponse)
async def upcoming_tasks(
    days: int = 7,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Tarefas com deadline_date nos próximos N dias, ativas.
    Usado pelo widget do dashboard."""
    from datetime import timedelta, date as _date

    filters = TaskFilters(
        deadline_before=_date.today() + timedelta(days=days),
        deadline_after=_date.today(),
        include_done=False,
        include_cancelled=False,
    )
    tasks = await task_service.list_tasks(workspace.id, filters, db=db)
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
    )


@router.get("/tasks/export.md", response_class=PlainTextResponse)
async def export_tasks_md(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Export do `tarefas.md` on-demand (compat pipeline legado — ADR-075)."""
    content = await task_service.export_markdown(workspace.id, db=db)
    return PlainTextResponse(content, media_type="text/markdown")


@router.post("/tasks/scan-deadlines", response_model=ScanDeadlinesResponse)
async def scan_deadlines(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ScanDeadlinesResponse:
    """Dispara o scan de prazos e cria notifications para tasks vencidas
    ou próximas (≤7 dias). Idempotente via dedup por title.

    Usado por:
    - Cron externo (ex: worker Celery beat em F8.3+)
    - UI: botão "Verificar alertas de prazo" (admin)
    """
    stats = await task_notification_service.scan_and_create_notifications(
        workspace.id, db=db
    )
    await db.commit()
    return ScanDeadlinesResponse(**stats)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(workspace.id, task_id, db=db)
    return TaskResponse.model_validate(task)


@router.get("/tasks/{task_id}/progress", response_model=TaskProgress)
async def get_task_progress(
    task_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """% executado no mês corrente para tasks de aporte (heurística).

    Retorna `is_trackable=False` se a task não é do tipo "aporte mensal".
    A UI (TaskDrawer) esconde o card de progresso nesse caso.
    """
    task = await task_service.get_task(workspace.id, task_id, db=db)
    storage = StorageService()
    tenant_root = str(storage.tenant_root(workspace.id))
    return task_progress_service.compute_progress(task, tenant_root=tenant_root)


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    payload: TaskCreate,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.create_task(
        workspace.id, payload, db=db, created_by=user.id
    )
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.update_task(
        workspace.id, task_id, payload, db=db
    )
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


@router.post(
    "/tasks/{task_id}/status",
    response_model=TaskResponse,
)
async def transition_task_status(
    task_id: str,
    payload: TaskStatusTransition,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Endpoint dedicado para transição de status. Separado do PATCH para
    deixar a audit-trail mais clara no Swagger / logs."""
    task = await task_service.transition_status(
        workspace.id,
        task_id,
        new_status=payload.status,
        db=db,
        reason=payload.status_reason,
    )
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


# ═══════════════════════════════════════════════════════════════════════
# Task Attachments (F8.3)
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/tasks/{task_id}/attachments",
    response_model=TaskAttachmentListResponse,
)
async def list_task_attachments(
    task_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    items = await task_attachment_service.list_attachments(
        workspace.id, task_id, db=db
    )
    return TaskAttachmentListResponse(
        attachments=[TaskAttachmentResponse.model_validate(a) for a in items],
        total=len(items),
    )


@router.post(
    "/tasks/{task_id}/attachments",
    response_model=TaskAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_task_attachment(
    task_id: str,
    file: UploadFile = File(...),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload multipart de um anexo. Valida extensão e tamanho via
    `StorageService.validate_file` (reusa o mesmo whitelist de documentos)."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo sem nome",
        )
    content = await file.read()
    attachment = await task_attachment_service.save_attachment(
        workspace.id,
        task_id,
        filename=file.filename,
        content=content,
        content_type=file.content_type,
        uploaded_by=user.id,
        db=db,
    )
    await db.commit()
    await db.refresh(attachment)
    return TaskAttachmentResponse.model_validate(attachment)


@router.get(
    "/tasks/{task_id}/attachments/{attachment_id}/download",
    response_class=FileResponse,
)
async def download_task_attachment(
    task_id: str,
    attachment_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Serve binário. Tenancy validado duas vezes: (1) get_current_workspace,
    (2) get_attachment filtra por workspace_id."""
    attachment = await task_attachment_service.get_attachment(
        workspace.id, attachment_id, db=db
    )
    if attachment.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo não pertence à task informada",
        )
    path = task_attachment_service.resolve_attachment_file(
        workspace.id, attachment
    )
    if path is None or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo ausente no storage",
        )
    return FileResponse(
        path,
        media_type=attachment.content_type or "application/octet-stream",
        filename=attachment.original_filename,
    )


@router.delete(
    "/tasks/{task_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task_attachment(
    task_id: str,
    attachment_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    attachment = await task_attachment_service.get_attachment(
        workspace.id, attachment_id, db=db
    )
    if attachment.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo não pertence à task informada",
        )
    await task_attachment_service.delete_attachment(
        workspace.id, attachment_id, db=db
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_task(
    task_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete: move para status='cancelled' preservando histórico.
    Para remoção física (raro, admin-only), fora do MVP."""
    await task_service.transition_status(
        workspace.id,
        task_id,
        new_status="cancelled",
        db=db,
        reason="Cancelada via DELETE",
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════════════════════
# Task Suggestions (fila do E5.N)
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/task-suggestions",
    response_model=TaskSuggestionListResponse,
)
async def list_suggestions(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = "pending",
):
    suggestions = await task_suggestion_service.list_pending(
        workspace.id, db=db, status=status_filter
    )
    return TaskSuggestionListResponse(
        suggestions=[
            TaskSuggestionResponse.model_validate(s) for s in suggestions
        ],
        total=len(suggestions),
    )


@router.post(
    "/task-suggestions",
    response_model=TaskSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_suggestion(
    body: TaskSuggestionCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Cria uma sugestão pending. Endpoint usado pelo E5.N (ADR-074) —
    pipeline LLM invoca via HTTP para gravar sugestões após rodar.

    Alternativa: chamar `task_suggestion_service.bulk_create` direto do
    Python dentro do worker. Este endpoint existe para workers em outros
    processos/linguagens (ex: pipeline CLI em transição)."""
    sugg = await task_suggestion_service.create_suggestion(
        workspace.id, body, db=db
    )
    await db.commit()
    await db.refresh(sugg)
    return TaskSuggestionResponse.model_validate(sugg)


@router.post(
    "/task-suggestions/{suggestion_id}/approve",
    response_model=TaskResponse,
)
async def approve_suggestion(
    suggestion_id: str,
    body: TaskSuggestionApprove,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, task = await task_suggestion_service.approve(
        workspace.id,
        suggestion_id,
        db=db,
        reviewed_by=user.id,
        body=body,
    )
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


@router.post(
    "/task-suggestions/{suggestion_id}/reject",
    response_model=TaskSuggestionResponse,
)
async def reject_suggestion(
    suggestion_id: str,
    body: TaskSuggestionReject,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sugg = await task_suggestion_service.reject(
        workspace.id,
        suggestion_id,
        db=db,
        reviewed_by=user.id,
        reason=body.reason,
    )
    await db.commit()
    await db.refresh(sugg)
    return TaskSuggestionResponse.model_validate(sugg)


@router.post(
    "/task-suggestions/{suggestion_id}/merge-into/{target_task_id}",
    response_model=TaskSuggestionResponse,
)
async def merge_suggestion_into(
    suggestion_id: str,
    target_task_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sugg = await task_suggestion_service.merge_into(
        workspace.id,
        suggestion_id,
        target_task_id,
        db=db,
        reviewed_by=user.id,
    )
    await db.commit()
    await db.refresh(sugg)
    return TaskSuggestionResponse.model_validate(sugg)
