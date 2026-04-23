"""Tasks API — thin router (A6e.4 slice · fase 4b · ADR-101 R15/R16).

Handlers de CRUD e TaskSuggestion delegam aos use cases em
``backend/app/application/task/``. Composites permanecem no router:

- ``export.md``: render markdown compat pipeline (``task_service.export_markdown``).
- ``scan-deadlines``: cross-aggregate Notification
  (``task_notification_service.scan_and_create_notifications``). Será
  reativo via evento em A6e.events-followup.
- ``progress``: Storage + heurística de aporte
  (``task_progress_service.compute_progress``).
- Upload/Download/Delete de anexos: side-effect de filesystem
  (``task_attachment_service``) — row via use case, arquivo via service.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.task import (
    approve_task_suggestion as _uc_approve_task_suggestion,
)
from backend.app.application.task import (
    cancel_task as _uc_cancel_task,
)
from backend.app.application.task import (
    create_task as _uc_create_task,
)
from backend.app.application.task import (
    create_task_suggestion as _uc_create_task_suggestion,
)
from backend.app.application.task import (
    delete_task_attachment as _uc_delete_task_attachment,
)
from backend.app.application.task import (
    get_task as _uc_get_task,
)
from backend.app.application.task import (
    list_task_attachments as _uc_list_task_attachments,
)
from backend.app.application.task import (
    list_task_suggestions as _uc_list_task_suggestions,
)
from backend.app.application.task import (
    list_workspace_tasks as _uc_list_workspace_tasks,
)
from backend.app.application.task import (
    merge_suggestion_into_task as _uc_merge_suggestion_into_task,
)
from backend.app.application.task import (
    reject_task_suggestion as _uc_reject_task_suggestion,
)
from backend.app.application.task import (
    transition_task_status as _uc_transition_task_status,
)
from backend.app.application.task import (
    update_task as _uc_update_task,
)
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.repositories.task_attachment_repository import (
    TaskAttachmentRepository,
)
from backend.app.repositories.task_repository import TaskRepository
from backend.app.repositories.task_suggestion_repository import (
    TaskSuggestionRepository,
)
from backend.app.schemas.dto.task import (
    ScanDeadlinesResponse,
    TaskAttachmentListResponse,
    TaskAttachmentResponse,
    TaskCreateCommand,
    TaskFilters,
    TaskListResponse,
    TaskProgressResponse,
    TaskResponse,
    TaskStatusTransitionCommand,
    TaskSuggestionApproveCommand,
    TaskSuggestionCreateCommand,
    TaskSuggestionListResponse,
    TaskSuggestionRejectCommand,
    TaskSuggestionResponse,
    TaskUpdateCommand,
    task_attachment_to_response,
)
from backend.app.services import (
    task_attachment_service,
    task_notification_service,
    task_progress_service,
    task_service,
)
from backend.app.services.storage import StorageService

router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["tasks"],
)


def _get_task_repo(db: AsyncSession = Depends(get_db)) -> TaskRepository:
    return TaskRepository(db)


def _get_suggestion_repo(
    db: AsyncSession = Depends(get_db),
) -> TaskSuggestionRepository:
    return TaskSuggestionRepository(db)


def _get_attachment_repo(
    db: AsyncSession = Depends(get_db),
) -> TaskAttachmentRepository:
    return TaskAttachmentRepository(db)


# ═══════════════════════════════════════════════════════════════════════
# Tasks
# ═══════════════════════════════════════════════════════════════════════


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    workspace: Workspace = Depends(get_current_workspace),
    repo: TaskRepository = Depends(_get_task_repo),
    status_filter: Optional[str] = None,  # evita conflito com import `status`
    priority: Optional[str] = None,
    category: Optional[str] = None,
    deadline_before: Optional[date] = None,
    deadline_after: Optional[date] = None,
    assigned_to: Optional[str] = None,
    related_goal_id: Optional[str] = None,
    include_done: bool = False,
    include_cancelled: bool = False,
) -> TaskListResponse:
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
    return await _uc_list_workspace_tasks(workspace.id, filters, repo=repo)


@router.get("/tasks/upcoming", response_model=TaskListResponse)
async def upcoming_tasks(
    days: int = 7,
    workspace: Workspace = Depends(get_current_workspace),
    repo: TaskRepository = Depends(_get_task_repo),
) -> TaskListResponse:
    """Tarefas com ``deadline_date`` nos próximos N dias, ativas. Widget do dashboard."""
    today = date.today()
    filters = TaskFilters(
        deadline_before=today + timedelta(days=days),
        deadline_after=today,
        include_done=False,
        include_cancelled=False,
    )
    return await _uc_list_workspace_tasks(workspace.id, filters, repo=repo)


@router.get("/tasks/export.md", response_class=PlainTextResponse)
async def export_tasks_md(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Export do ``tarefas.md`` (compat pipeline legado — ADR-075)."""
    content = await task_service.export_markdown(workspace.id, db=db)
    return PlainTextResponse(content, media_type="text/markdown")


@router.post("/tasks/scan-deadlines", response_model=ScanDeadlinesResponse)
async def scan_deadlines(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> ScanDeadlinesResponse:
    """Dispara scan de prazos + cria notifications para tasks vencidas ou ≤7 dias.

    Composite (cross-aggregate Notification). Migração para evento reativo
    em A6e.events-followup (flag ``USE_EVENT_DRIVEN_TASK_NOTIFICATIONS``).
    """
    stats = await task_notification_service.scan_and_create_notifications(workspace.id, db=db)
    await db.commit()
    return ScanDeadlinesResponse(**stats)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    repo: TaskRepository = Depends(_get_task_repo),
) -> TaskResponse:
    return await _uc_get_task(workspace.id, task_id, repo=repo)


@router.get("/tasks/{task_id}/progress", response_model=TaskProgressResponse)
async def get_task_progress(
    task_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> TaskProgressResponse:
    """% executado no mês para tasks de aporte (heurística).

    Composite — depende de Storage tenant root e do progress_service.
    Use case puro retorna só a Task; cálculo fica aqui.
    """
    task = await task_service.get_task(workspace.id, task_id, db=db)
    storage = StorageService()
    tenant_root = str(storage.tenant_root(workspace.id))
    return task_progress_service.compute_progress(
        task, workspace_id=workspace.id, tenant_root=tenant_root
    )


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    payload: TaskCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: TaskRepository = Depends(_get_task_repo),
) -> TaskResponse:
    response = await _uc_create_task(
        payload, workspace_id=workspace.id, repo=repo, created_by=user.id, db=db
    )
    await db.commit()
    return response


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    payload: TaskUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: TaskRepository = Depends(_get_task_repo),
) -> TaskResponse:
    response = await _uc_update_task(
        payload,
        workspace_id=workspace.id,
        task_id=task_id,
        repo=repo,
        db=db,
        actor_user_id=user.id,
    )
    await db.commit()
    return response


@router.post(
    "/tasks/{task_id}/status",
    response_model=TaskResponse,
)
async def transition_task_status(
    task_id: str,
    payload: TaskStatusTransitionCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: TaskRepository = Depends(_get_task_repo),
) -> TaskResponse:
    """Endpoint dedicado para transição de status. Separado do PATCH para
    audit-trail mais clara em Swagger / logs."""
    response = await _uc_transition_task_status(
        workspace.id,
        task_id,
        new_status=payload.status,
        repo=repo,
        reason=payload.status_reason,
    )
    await db.commit()
    return response


# ═══════════════════════════════════════════════════════════════════════
# Task Attachments
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/tasks/{task_id}/attachments",
    response_model=TaskAttachmentListResponse,
)
async def list_task_attachments(
    task_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    task_repo: TaskRepository = Depends(_get_task_repo),
    attachment_repo: TaskAttachmentRepository = Depends(_get_attachment_repo),
) -> TaskAttachmentListResponse:
    return await _uc_list_task_attachments(
        workspace.id,
        task_id,
        task_repo=task_repo,
        attachment_repo=attachment_repo,
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
) -> TaskAttachmentResponse:
    """Upload multipart. Composite de Storage (valida extensão + tamanho
    via whitelist de documentos)."""
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
    return task_attachment_to_response(attachment)


@router.get(
    "/tasks/{task_id}/attachments/{attachment_id}/download",
    response_class=FileResponse,
)
async def download_task_attachment(
    task_id: str,
    attachment_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Serve binário. Composite de Storage (FileResponse do disco).

    Tenancy validado duas vezes: (1) ``get_current_workspace``,
    (2) ``get_attachment`` filtra por ``workspace_id``.
    """
    attachment = await task_attachment_service.get_attachment(workspace.id, attachment_id, db=db)
    if attachment.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo não pertence à task informada",
        )
    path = task_attachment_service.resolve_attachment_file(workspace.id, attachment)
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
    repo: TaskAttachmentRepository = Depends(_get_attachment_repo),
) -> Response:
    """Remove row + arquivo físico. Use case retorna a entidade para o
    router resolver o path antes do commit e remover o arquivo depois."""
    attachment = await _uc_delete_task_attachment(workspace.id, task_id, attachment_id, repo=repo)
    path = task_attachment_service.resolve_attachment_file(workspace.id, attachment)
    await db.commit()
    if path is not None and path.is_file():
        path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_task(
    task_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: TaskRepository = Depends(_get_task_repo),
) -> Response:
    """Soft-delete: move para ``status='cancelled'`` preservando histórico."""
    await _uc_cancel_task(workspace.id, task_id, repo=repo)
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
    repo: TaskSuggestionRepository = Depends(_get_suggestion_repo),
    status_filter: Optional[str] = "pending",
) -> TaskSuggestionListResponse:
    return await _uc_list_task_suggestions(workspace.id, repo=repo, status=status_filter)


@router.post(
    "/task-suggestions",
    response_model=TaskSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_suggestion(
    body: TaskSuggestionCreateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    repo: TaskSuggestionRepository = Depends(_get_suggestion_repo),
) -> TaskSuggestionResponse:
    """Cria sugestão pending. Usado pelo E5.N (ADR-074) — pipeline LLM
    invoca via HTTP para gravar propostas após rodar."""
    response = await _uc_create_task_suggestion(body, workspace_id=workspace.id, repo=repo)
    await db.commit()
    return response


@router.post(
    "/task-suggestions/{suggestion_id}/approve",
    response_model=TaskResponse,
)
async def approve_suggestion(
    suggestion_id: str,
    body: TaskSuggestionApproveCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    task_repo: TaskRepository = Depends(_get_task_repo),
    suggestion_repo: TaskSuggestionRepository = Depends(_get_suggestion_repo),
) -> TaskResponse:
    _, task_resp = await _uc_approve_task_suggestion(
        workspace.id,
        suggestion_id,
        suggestion_repo=suggestion_repo,
        task_repo=task_repo,
        reviewed_by=user.id,
        body=body,
    )
    await db.commit()
    return task_resp


@router.post(
    "/task-suggestions/{suggestion_id}/reject",
    response_model=TaskSuggestionResponse,
)
async def reject_suggestion(
    suggestion_id: str,
    body: TaskSuggestionRejectCommand,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: TaskSuggestionRepository = Depends(_get_suggestion_repo),
) -> TaskSuggestionResponse:
    response = await _uc_reject_task_suggestion(
        workspace.id,
        suggestion_id,
        repo=repo,
        reviewed_by=user.id,
        reason=body.reason,
    )
    await db.commit()
    return response


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
    task_repo: TaskRepository = Depends(_get_task_repo),
    suggestion_repo: TaskSuggestionRepository = Depends(_get_suggestion_repo),
) -> TaskSuggestionResponse:
    response = await _uc_merge_suggestion_into_task(
        workspace.id,
        suggestion_id,
        target_task_id,
        suggestion_repo=suggestion_repo,
        task_repo=task_repo,
        reviewed_by=user.id,
    )
    await db.commit()
    return response
