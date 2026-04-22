"""TaskRepository — CRUD async para o agregado ``Task``.

Encapsula as queries sobre ``tasks`` para que o service orquestre as
regras de domínio (transições válidas, dependency check de parent,
audit trail) sem construir SQL ad-hoc (R13).

R14 (ADR-101): repo **não commita** — caller é dono do boundary
transacional. O service fecha o commit no fim do fluxo (ex.: approve
de sugestão = create task + update suggestion + commit uma vez só).

Por design, ``TaskAttachment`` e ``TaskSuggestion`` têm repositórios
**separados** apesar de morarem na mesma tabela-vizinha. Motivo:

- ``TaskAttachment``: aggregate próprio — ciclo de vida ligado a
  ``Task`` mas com operações de storage (FS/MinIO) que o caller
  (service) compõe. Repo só fala DB.
- ``TaskSuggestion``: aggregate de fluxo (pending → approved/rejected/
  merged). Não é "parte" de uma Task — é o **pré-estado** opcional.

Uso::

    repo = TaskRepository(session)
    tasks = await repo.list(ws_id, filters)
    task = await repo.get_by_id(ws_id, task_id)
    next_n = await repo.next_number(ws_id)
    task = await repo.add(new_task)
    await session.commit()
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.task import Task
from backend.app.schemas.task import TaskFilters


class TaskRepository:
    """Single Responsibility: persistência do agregado ``Task``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def list(
        self,
        workspace_id: str,
        filters: TaskFilters,
    ) -> list[Task]:
        """Lista tasks aplicando ``filters``.

        Ordenação preserva a semântica do service legado: prioridade
        ``S → R → O`` via ``CASE`` (inverte o ``upper()`` alfabético
        que daria ``O < R < S``), depois ``deadline_date`` ascendente
        (``NULL`` por último), depois ``number`` asc.

        Filtro de status:

        - ``filters.status`` setado → ``WHERE status = X``.
        - Default: exclui ``done`` / ``cancelled`` a menos que
          ``include_done`` / ``include_cancelled`` sejam true.
        """
        stmt = select(Task).where(Task.workspace_id == workspace_id)

        if filters.status is not None:
            stmt = stmt.where(Task.status == filters.status)
        else:
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

        priority_rank = case(
            (func.upper(Task.priority) == "S", 1),
            (func.upper(Task.priority) == "R", 2),
            (func.upper(Task.priority) == "O", 3),
            else_=99,
        )
        stmt = stmt.order_by(
            priority_rank,
            Task.deadline_date.is_(None),
            Task.deadline_date.asc(),
            Task.number.asc(),
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, workspace_id: str) -> list[Task]:
        """Lista TODAS as tasks do workspace (inclui done/cancelled).

        Usado pelo ``export_markdown`` — ordenação por ``number`` asc
        para preservar ordem histórica do ``tarefas.md`` legado.
        """
        result = await self._session.execute(
            select(Task).where(Task.workspace_id == workspace_id).order_by(Task.number.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, workspace_id: str, task_id: str) -> Optional[Task]:
        """Retorna task por id dentro do workspace, ou ``None``."""
        result = await self._session.execute(
            select(Task).where(
                Task.workspace_id == workspace_id,
                Task.id == task_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_number(self, workspace_id: str, number: int) -> Optional[Task]:
        """Retorna task por ``number`` (único por workspace) ou ``None``."""
        result = await self._session.execute(
            select(Task).where(
                Task.workspace_id == workspace_id,
                Task.number == number,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_parent(self, workspace_id: str, parent_task_id: str) -> list[Task]:
        """Retorna subtasks (filhos diretos) de uma task."""
        result = await self._session.execute(
            select(Task)
            .where(
                Task.workspace_id == workspace_id,
                Task.parent_task_id == parent_task_id,
            )
            .order_by(Task.number.asc())
        )
        return list(result.scalars().all())

    async def next_number(self, workspace_id: str) -> int:
        """``max(number) + 1`` no workspace — chamada dentro da transação
        que vai inserir, para evitar race com outros INSERTs.

        Retorna ``1`` se o workspace ainda não tem tasks.
        """
        result = await self._session.execute(
            select(func.max(Task.number)).where(Task.workspace_id == workspace_id)
        )
        current_max = result.scalar_one_or_none()
        return (current_max or 0) + 1

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def add(self, task: Task, *, flush: bool = True) -> Task:
        """Registra ``task`` na sessão; retorna a instância.

        ``flush=True`` (default) emite INSERT agora para materializar o
        id e disparar violações do unique ``(workspace_id, number)``
        antes do commit final. Caller é sempre responsável pelo commit.
        """
        self._session.add(task)
        if flush:
            await self._session.flush()
        return task

    async def save(self, task: Task) -> Task:
        """Marca a entidade como dirty e dá flush (sem commit).

        Útil após mutations manuais (``task.status = 'done'``) — força o
        UPDATE a subir agora para o caller validar constraints. Não
        chama ``session.add`` por ser no-op em entities já carregadas,
        mas chamá-lo não prejudica (idempotente).
        """
        self._session.add(task)
        await self._session.flush()
        return task

    async def delete(self, task: Task) -> None:
        """Remove a row (ORM delete, sem commit).

        Em produção, o router faz soft-delete via ``status=cancelled`` —
        este método existe para casos admin-only / testes.
        """
        await self._session.delete(task)
