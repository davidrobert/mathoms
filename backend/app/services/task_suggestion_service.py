"""TaskSuggestion service — ADR-074.

Queue de sugestões do E5.N (ou regras do sistema) aguardando aprovação
humana. Workflow:

    1. E5.N gera sugestões → bulk_create (status=pending)
    2. Usuário vê em /plano-de-acao/sugestoes
    3. Aprovar → materializa Task + marca suggestion(status=approved,
       approved_task_id=...)
    4. Rejeitar → suggestion(status=rejected, rejection_reason=...)
    5. Merge (opcional): anexa sugestão a Task existente sem criar
       duplicata (status=merged, approved_task_id = task_existente)

Persistência delegada ao ``TaskSuggestionRepository``. Criação da Task
na aprovação passa pelo ``task_service.create_task`` (mesma validação
+ numeração atômica).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.task import Task, TaskSuggestion
from backend.app.repositories.task_suggestion_repository import (
    TaskSuggestionRepository,
)
from backend.app.schemas.dto.task import (
    TaskCreateCommand,
    TaskSuggestionApproveCommand,
    TaskSuggestionCreateCommand,
)
from backend.app.services import task_service


async def list_pending(
    workspace_id: str,
    *,
    db: AsyncSession,
    status: Optional[str] = "pending",
) -> list[TaskSuggestion]:
    repo = TaskSuggestionRepository(db)
    return await repo.list_by_status(workspace_id, status=status)


async def get_suggestion(
    workspace_id: str,
    suggestion_id: str,
    *,
    db: AsyncSession,
) -> TaskSuggestion:
    repo = TaskSuggestionRepository(db)
    sugg = await repo.get_by_id(workspace_id, suggestion_id)
    if sugg is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Sugestão não encontrada",
        )
    return sugg


async def create_suggestion(
    workspace_id: str,
    payload: TaskSuggestionCreateCommand,
    *,
    db: AsyncSession,
) -> TaskSuggestion:
    sugg = TaskSuggestion(
        workspace_id=workspace_id,
        proposed_payload=payload.proposed_payload.model_dump(),
        source=payload.source,
        source_run_id=payload.source_run_id,
        status="pending",
    )
    repo = TaskSuggestionRepository(db)
    return await repo.add(sugg)


async def bulk_create(
    workspace_id: str,
    suggestions: list[TaskSuggestionCreateCommand],
    *,
    db: AsyncSession,
) -> list[TaskSuggestion]:
    """Uso do E5.N: insere várias sugestões no fim de um run de pipeline."""
    created: list[TaskSuggestion] = []
    for s in suggestions:
        created.append(await create_suggestion(workspace_id, s, db=db))
    return created


async def approve(
    workspace_id: str,
    suggestion_id: str,
    *,
    db: AsyncSession,
    reviewed_by: Optional[str] = None,
    body: Optional[TaskSuggestionApproveCommand] = None,
) -> tuple[TaskSuggestion, Task]:
    """Aprova sugestão: materializa Task + marca suggestion como approved.

    Body opcional permite o usuário editar o payload antes de aceitar —
    se fornecido, sobrescreve ``proposed_payload``.
    """
    sugg = await get_suggestion(workspace_id, suggestion_id, db=db)
    if sugg.status != "pending":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Sugestão já foi processada (status={sugg.status})",
        )

    # Decide payload final
    if body and body.edited_payload:
        task_payload = body.edited_payload.model_dump()
    else:
        task_payload = sugg.proposed_payload

    # Converte para TaskCreateCommand (reusa validação)
    task_create = TaskCreateCommand(**task_payload)

    task = await task_service.create_task(
        workspace_id,
        task_create,
        db=db,
        created_by=reviewed_by,
        created_from="llm_suggestion",
        source_suggestion_id=sugg.id,
    )

    sugg.status = "approved"
    sugg.reviewed_by = reviewed_by
    sugg.reviewed_at = datetime.now(timezone.utc)
    sugg.approved_task_id = task.id
    repo = TaskSuggestionRepository(db)
    await repo.save(sugg)
    return sugg, task


async def reject(
    workspace_id: str,
    suggestion_id: str,
    *,
    db: AsyncSession,
    reviewed_by: Optional[str] = None,
    reason: Optional[str] = None,
) -> TaskSuggestion:
    sugg = await get_suggestion(workspace_id, suggestion_id, db=db)
    if sugg.status != "pending":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Sugestão já foi processada (status={sugg.status})",
        )
    sugg.status = "rejected"
    sugg.rejection_reason = reason
    sugg.reviewed_by = reviewed_by
    sugg.reviewed_at = datetime.now(timezone.utc)
    repo = TaskSuggestionRepository(db)
    return await repo.save(sugg)


async def merge_into(
    workspace_id: str,
    suggestion_id: str,
    target_task_id: str,
    *,
    db: AsyncSession,
    reviewed_by: Optional[str] = None,
) -> TaskSuggestion:
    """Anexa sugestão a task existente (não cria nova).

    Útil quando E5.N sugere "revisar taxa PGBL" mas já existe task #18
    para isso.
    """
    sugg = await get_suggestion(workspace_id, suggestion_id, db=db)
    if sugg.status != "pending":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Sugestão já foi processada (status={sugg.status})",
        )
    # Valida que a task alvo pertence ao mesmo workspace.
    target = await task_service.get_task(workspace_id, target_task_id, db=db)
    sugg.status = "merged"
    sugg.approved_task_id = target.id
    sugg.reviewed_by = reviewed_by
    sugg.reviewed_at = datetime.now(timezone.utc)
    repo = TaskSuggestionRepository(db)
    return await repo.save(sugg)


__all__ = [
    "approve",
    "bulk_create",
    "create_suggestion",
    "get_suggestion",
    "list_pending",
    "merge_into",
    "reject",
]
