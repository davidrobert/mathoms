"""Task service — ADR-074.

Responsabilidades:
- CRUD de `Task` (criação com auto-número, update parcial)
- Transições de status validadas (pending↔in_progress↔done/cancelled/blocked)
- Enforcement de dependência: `status=done` bloqueado se parent ainda pendente
- Listagem filtrada
- Export para markdown (compat pipeline legado, ADR-075)

Todas as funções recebem `workspace_id` como primeiro argumento —
padrão ADR-072.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.task import (
    Task,
    VALID_CATEGORIES,
    VALID_PRIORITIES,
    VALID_STATUSES,
)
from backend.app.schemas.task import (
    TaskCreate,
    TaskFilters,
    TaskUpdate,
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


# ─── Helpers ───────────────────────────────────────────────────────────


async def _next_task_number(workspace_id: str, db: AsyncSession) -> int:
    """max(number)+1 por workspace — chamada dentro da mesma transação
    que o INSERT para evitar race."""
    stmt = select(func.max(Task.number)).where(Task.workspace_id == workspace_id)
    result = await db.execute(stmt)
    current_max = result.scalar_one_or_none()
    return (current_max or 0) + 1


def _validate_vocab(payload: TaskCreate | TaskUpdate) -> None:
    """Valida campos de vocabulário (category, priority, status) contra
    os sets do model. Pydantic já valida Literal types, mas `category`
    é string livre — aqui rejeitamos out-of-vocab."""
    cat = getattr(payload, "category", None)
    if cat is not None and cat not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Categoria inválida: '{cat}'. "
                f"Aceitas: {sorted(VALID_CATEGORIES)}"
            ),
        )


# ─── CRUD ──────────────────────────────────────────────────────────────


async def list_tasks(
    workspace_id: str,
    filters: TaskFilters,
    *,
    db: AsyncSession,
) -> list[Task]:
    """Lista tasks filtradas. Ordena por priority (S→R→O) + deadline_date."""
    stmt = select(Task).where(Task.workspace_id == workspace_id)

    if filters.status is not None:
        stmt = stmt.where(Task.status == filters.status)
    else:
        # Default: não mostra done/cancelled exceto se solicitado
        excluded: list[str] = []
        if not filters.include_done:
            excluded.append("done")
        if not filters.include_cancelled:
            excluded.append("cancelled")
        if excluded:
            stmt = stmt.where(Task.status.not_in(excluded))

    if filters.priority is not None:
        stmt = stmt.where(Task.priority == filters.priority)
    if filters.category is not None:
        stmt = stmt.where(Task.category == filters.category)
    if filters.deadline_before is not None:
        stmt = stmt.where(Task.deadline_date <= filters.deadline_before)
    if filters.deadline_after is not None:
        stmt = stmt.where(Task.deadline_date >= filters.deadline_after)
    if filters.assigned_to is not None:
        stmt = stmt.where(Task.assigned_to == filters.assigned_to)
    if filters.related_goal_id is not None:
        stmt = stmt.where(Task.related_goal_id == filters.related_goal_id)

    # Ordenação: S antes de R antes de O; depois deadline_date ascendente
    # Order by priority (S < R < O semanticamente), depois por deadline,
    # depois por número. ``func.upper`` produz ordem alfabética O<R<S, que
    # é o INVERSO do que queremos. Usamos CASE para mapear a ordem correta:
    # S=1 (Standard, mais importante) → R=2 → O=3 (Optional, último).
    priority_rank = case(
        (func.upper(Task.priority) == "S", 1),
        (func.upper(Task.priority) == "R", 2),
        (func.upper(Task.priority) == "O", 3),
        else_=99,
    )
    stmt = stmt.order_by(
        priority_rank,
        Task.deadline_date.is_(None),  # False (tem data) vem antes
        Task.deadline_date.asc(),
        Task.number.asc(),
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_task(
    workspace_id: str,
    task_id: str,
    *,
    db: AsyncSession,
) -> Task:
    """Retorna uma Task do workspace ou 404."""
    stmt = select(Task).where(
        Task.workspace_id == workspace_id, Task.id == task_id
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Tarefa não encontrada",
        )
    return task


async def create_task(
    workspace_id: str,
    payload: TaskCreate,
    *,
    db: AsyncSession,
    created_by: Optional[str] = None,
    created_from: str = "manual",
    source_suggestion_id: Optional[str] = None,
) -> Task:
    _validate_vocab(payload)

    # Validação: parent_task_id, se informado, deve pertencer ao mesmo workspace
    if payload.parent_task_id:
        parent_stmt = select(Task).where(
            Task.workspace_id == workspace_id,
            Task.id == payload.parent_task_id,
        )
        parent = (await db.execute(parent_stmt)).scalar_one_or_none()
        if parent is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="parent_task_id inválido (não pertence ao workspace)",
            )

    number = payload.number or await _next_task_number(workspace_id, db)

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
    db.add(task)
    await db.flush()
    return task


async def update_task(
    workspace_id: str,
    task_id: str,
    payload: TaskUpdate,
    *,
    db: AsyncSession,
) -> Task:
    _validate_vocab(payload)
    task = await get_task(workspace_id, task_id, db=db)

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
    db.add(task)
    await db.flush()
    return task


async def transition_status(
    workspace_id: str,
    task_id: str,
    *,
    new_status: str,
    db: AsyncSession,
    reason: Optional[str] = None,
) -> Task:
    """Transição validada de status. Enforça:
    - status de destino é válido (VALID_STATUSES)
    - transição é aceita (ALLOWED_TRANSITIONS)
    - se `done` e há parent_task_id, parent precisa estar em {done, cancelled}
    """
    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Status inválido: {new_status}",
        )

    task = await get_task(workspace_id, task_id, db=db)
    if task.status == new_status:
        return task

    allowed = ALLOWED_TRANSITIONS.get(task.status, frozenset())
    if new_status not in allowed:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Transição não permitida: {task.status} → {new_status}. "
                f"Aceitas a partir de '{task.status}': {sorted(allowed)}"
            ),
        )

    if new_status == "done" and task.parent_task_id:
        parent_stmt = select(Task).where(
            Task.workspace_id == workspace_id,
            Task.id == task.parent_task_id,
        )
        parent = (await db.execute(parent_stmt)).scalar_one_or_none()
        if parent is not None and parent.status not in ("done", "cancelled"):
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=(
                    f"Parent task #{parent.number} ({parent.status}) não "
                    f"está concluída. Conclua a dependência primeiro."
                ),
            )

    task.status = new_status
    task.status_reason = reason
    now = datetime.now(timezone.utc)
    if new_status == "done":
        task.completed_at = now
    if new_status == "cancelled":
        task.cancelled_at = now
    # Reabrir de done/cancelled → zera timestamps correspondentes
    if new_status in ("pending", "in_progress"):
        task.completed_at = None
        task.cancelled_at = None

    db.add(task)
    await db.flush()
    return task


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


async def export_markdown(
    workspace_id: str,
    *,
    db: AsyncSession,
) -> str:
    """Gera o conteúdo de `tarefas.md` a partir do DB, preservando o
    formato do arquivo legado (tabelas por prioridade + histórico)."""
    # tenancy garantida na query — list_tasks filtra por workspace_id
    stmt = (
        select(Task)
        .where(Task.workspace_id == workspace_id)
        .order_by(Task.number.asc())
    )
    all_tasks = list((await db.execute(stmt)).scalars().all())

    lines: list[str] = []
    lines.append("# Tarefas — Pipeline (export do DB)")
    lines.append("")
    lines.append(
        "> Gerado por `task_service.export_markdown`. "
        "Fonte de verdade: tabela `tasks` (ADR-074)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    active = [t for t in all_tasks if t.status not in ("done", "cancelled")]
    done = [t for t in all_tasks if t.status == "done"]

    for prio in ("S", "R", "O"):
        section_tasks = [t for t in active if t.priority == prio]
        if not section_tasks:
            continue
        lines.append(f"## {_PRIORITY_SECTION[prio]}")
        lines.append("")
        lines.append("| # | Tarefa | Categoria | Prazo | Status | Ref |")
        lines.append("|---|---|---|---|---|---|")
        for t in section_tasks:
            prazo = (
                t.deadline_label
                or (t.deadline_date.isoformat() if t.deadline_date else "—")
            )
            ref = t.ref or "—"
            title = t.title.replace("|", "\\|")
            lines.append(
                f"| {t.number} | {title} | {t.category} | {prazo} | "
                f"{_STATUS_MD_LABEL.get(t.status, t.status)} | {ref} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    if done:
        lines.append("## Concluídas (histórico)")
        lines.append("")
        lines.append("| # | Tarefa | Data conclusão | Detalhe |")
        lines.append("|---|---|---|---|")
        for t in done:
            completed = (
                t.completed_at.date().isoformat() if t.completed_at else "—"
            )
            title = t.title.replace("|", "\\|")
            lines.append(
                f"| {t.number} | {title} | {completed} | "
                f"{t.status_reason or '—'} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


__all__ = [
    "ALLOWED_TRANSITIONS",
    "list_tasks",
    "get_task",
    "create_task",
    "update_task",
    "transition_status",
    "export_markdown",
]
