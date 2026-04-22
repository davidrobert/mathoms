"""Task service — ADR-074.

Orquestração de regras de domínio:
- CRUD de ``Task`` (criação com auto-número via repo, update parcial).
- Transições de status validadas (grafo ``ALLOWED_TRANSITIONS``).
- Enforcement de dependência: ``status=done`` bloqueado se parent
  ainda está pending/in_progress/blocked.
- Listagem filtrada (delegada ao repo + TaskFilters).
- Export para markdown (compat pipeline legado, ADR-075).

Persistência vive em ``TaskRepository``. Todas as funções recebem
``workspace_id`` como primeiro argumento — padrão ADR-072.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.task import (
    VALID_CATEGORIES,
    VALID_STATUSES,
    Task,
)
from backend.app.repositories.task_repository import TaskRepository
from backend.app.schemas.dto.task import (
    TaskCreateCommand,
    TaskFilters,
    TaskUpdateCommand,
)

# ─── Transições válidas ────────────────────────────────────────────────

# Grafo: de → set de destinos aceitos.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"in_progress", "done", "cancelled", "blocked"}),
    "in_progress": frozenset({"pending", "done", "cancelled", "blocked"}),
    "blocked": frozenset({"pending", "in_progress", "cancelled"}),
    # Terminais — mas permitimos reabrir explicitamente (audit trail via
    # status_reason + updated_at)
    "done": frozenset({"pending", "in_progress"}),
    "cancelled": frozenset({"pending"}),
}


# ─── Validações de domínio ─────────────────────────────────────────────


def _validate_vocab(payload: TaskCreateCommand | TaskUpdateCommand) -> None:
    """Valida ``category`` contra ``VALID_CATEGORIES`` (string livre no
    Pydantic, enum no domínio).

    ``priority`` e ``status`` já são ``Literal`` — Pydantic rejeita antes.
    """
    cat = getattr(payload, "category", None)
    if cat is not None and cat not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(f"Categoria inválida: '{cat}'. " f"Aceitas: {sorted(VALID_CATEGORIES)}"),
        )


# ─── CRUD ──────────────────────────────────────────────────────────────


async def list_tasks(
    workspace_id: str,
    filters: TaskFilters,
    *,
    db: AsyncSession,
) -> list[Task]:
    """Lista tasks filtradas. Ordenação S→R→O + deadline asc + number asc."""
    repo = TaskRepository(db)
    return await repo.list(workspace_id, filters)


async def get_task(
    workspace_id: str,
    task_id: str,
    *,
    db: AsyncSession,
) -> Task:
    """Retorna uma Task do workspace ou 404."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(workspace_id, task_id)
    if task is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Tarefa não encontrada",
        )
    return task


async def create_task(
    workspace_id: str,
    payload: TaskCreateCommand,
    *,
    db: AsyncSession,
    created_by: Optional[str] = None,
    created_from: str = "manual",
    source_suggestion_id: Optional[str] = None,
) -> Task:
    _validate_vocab(payload)
    repo = TaskRepository(db)

    # Parent, se informado, tem que pertencer ao mesmo workspace.
    if payload.parent_task_id:
        parent = await repo.get_by_id(workspace_id, payload.parent_task_id)
        if parent is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="parent_task_id inválido (não pertence ao workspace)",
            )

    number = payload.number or await repo.next_number(workspace_id)

    task = Task(
        workspace_id=workspace_id,
        number=number,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        deadline_kind=payload.deadline_kind,
        deadline_date=payload.deadline_date,
        deadline_label=payload.deadline_label,
        ref=payload.ref,
        parent_task_id=payload.parent_task_id,
        related_transaction_id=payload.related_transaction_id,
        related_goal_id=payload.related_goal_id,
        assigned_to=payload.assigned_to,
        created_by=created_by,
        created_from=created_from,
        source_suggestion_id=source_suggestion_id,
        status="pending",
    )
    return await repo.add(task)


async def update_task(
    workspace_id: str,
    task_id: str,
    payload: TaskUpdateCommand,
    *,
    db: AsyncSession,
) -> Task:
    _validate_vocab(payload)
    task = await get_task(workspace_id, task_id, db=db)
    repo = TaskRepository(db)

    # Mudança de status passa pela função dedicada (validação + timestamp)
    if payload.status is not None and payload.status != task.status:
        await transition_status(
            workspace_id,
            task_id,
            new_status=payload.status,
            db=db,
            reason=payload.status_reason,
        )
        # Re-lê para pegar campos timestamp atualizados
        await db.refresh(task)

    data = payload.model_dump(exclude_unset=True, exclude={"status", "status_reason"})
    for key, value in data.items():
        setattr(task, key, value)
    return await repo.save(task)


def _validate_transition(current_status: str, new_status: str) -> None:
    """Enforça VALID_STATUSES + ALLOWED_TRANSITIONS. Raise HTTPException."""
    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Status inválido: {new_status}",
        )
    allowed = ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if new_status not in allowed:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Transição não permitida: {current_status} → {new_status}. "
                f"Aceitas a partir de '{current_status}': {sorted(allowed)}"
            ),
        )


async def _assert_parent_done_before_completing(
    task: Task,
    *,
    repo: TaskRepository,
    workspace_id: str,
) -> None:
    """Se task.parent_task_id existe, parent precisa estar em done/cancelled."""
    if not task.parent_task_id:
        return
    parent = await repo.get_by_id(workspace_id, task.parent_task_id)
    if parent is not None and parent.status not in ("done", "cancelled"):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Parent task #{parent.number} ({parent.status}) não "
                f"está concluída. Conclua a dependência primeiro."
            ),
        )


def _apply_status_timestamps(task: Task, new_status: str) -> None:
    """Ajusta completed_at/cancelled_at conforme destino da transição."""
    now = datetime.now(timezone.utc)
    if new_status == "done":
        task.completed_at = now
    elif new_status == "cancelled":
        task.cancelled_at = now
    elif new_status in ("pending", "in_progress"):
        # Reabrir de done/cancelled → zera timestamps correspondentes
        task.completed_at = None
        task.cancelled_at = None


async def transition_status(
    workspace_id: str,
    task_id: str,
    *,
    new_status: str,
    db: AsyncSession,
    reason: Optional[str] = None,
) -> Task:
    """Transição validada de status. Enforça valores válidos + transições
    aceitas + parent done quando completando filha."""
    repo = TaskRepository(db)
    task = await get_task(workspace_id, task_id, db=db)
    if task.status == new_status:
        return task

    _validate_transition(task.status, new_status)
    if new_status == "done":
        await _assert_parent_done_before_completing(task, repo=repo, workspace_id=workspace_id)

    task.status = new_status
    task.status_reason = reason
    _apply_status_timestamps(task, new_status)
    return await repo.save(task)


# ─── Export markdown (compat pipeline legado — ADR-075) ────────────────


_PRIORITY_SECTION = {
    "S": "Essenciais (S)",
    "R": "Recomendadas (R)",
    "O": "Opcionais (O)",
}

# Para o MD: mapeia status interno → label exibido (preserva vocabulário
# original do tarefas.md).
_STATUS_MD_LABEL = {
    "pending": "pendente",
    "in_progress": "em andamento",
    "done": "feito",
    "cancelled": "cancelado",
    "blocked": "bloqueado",
}


def _md_export_header_lines() -> list[str]:
    return [
        "# Tarefas — Pipeline (export do DB)",
        "",
        "> Gerado por `task_service.export_markdown`. "
        "Fonte de verdade: tabela `tasks` (ADR-074).",
        "",
        "---",
        "",
    ]


def _md_priority_block_lines(priority: str, tasks: list[Task]) -> list[str]:
    """Bloco de seção S/R/O. Vazio se não há tasks."""
    if not tasks:
        return []
    lines = [
        f"## {_PRIORITY_SECTION[priority]}",
        "",
        "| # | Tarefa | Categoria | Prazo | Status | Ref |",
        "|---|---|---|---|---|---|",
    ]
    for t in tasks:
        prazo = t.deadline_label or (t.deadline_date.isoformat() if t.deadline_date else "—")
        title = t.title.replace("|", "\\|")
        lines.append(
            f"| {t.number} | {title} | {t.category} | {prazo} | "
            f"{_STATUS_MD_LABEL.get(t.status, t.status)} | {t.ref or '—'} |"
        )
    lines.extend(["", "---", ""])
    return lines


def _md_done_block_lines(done_tasks: list[Task]) -> list[str]:
    """Bloco histórico de concluídas. Vazio se não há."""
    if not done_tasks:
        return []
    lines = [
        "## Concluídas (histórico)",
        "",
        "| # | Tarefa | Data conclusão | Detalhe |",
        "|---|---|---|---|",
    ]
    for t in done_tasks:
        completed = t.completed_at.date().isoformat() if t.completed_at else "—"
        title = t.title.replace("|", "\\|")
        lines.append(f"| {t.number} | {title} | {completed} | {t.status_reason or '—'} |")
    lines.append("")
    return lines


async def export_markdown(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> str:
    """Gera o conteúdo de ``tarefas.md`` a partir do DB, preservando o
    formato do arquivo legado (tabelas por prioridade + histórico)."""
    repo = TaskRepository(db)
    all_tasks = await repo.list_all(workspace_id)
    active = [t for t in all_tasks if t.status not in ("done", "cancelled")]
    done = [t for t in all_tasks if t.status == "done"]

    lines: list[str] = _md_export_header_lines()
    for prio in ("S", "R", "O"):
        section_tasks = [t for t in active if t.priority == prio]
        lines.extend(_md_priority_block_lines(prio, section_tasks))
    lines.extend(_md_done_block_lines(done))
    return "\n".join(lines) + "\n"


__all__ = [
    "ALLOWED_TRANSITIONS",
    "create_task",
    "export_markdown",
    "get_task",
    "list_tasks",
    "transition_status",
    "update_task",
]
