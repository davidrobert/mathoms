"""TaskSuggestionRepository — CRUD async para ``TaskSuggestion``.

Queue de sugestões do E5.N ou regras do sistema aguardando aprovação
(workflow pending → approved/rejected/merged). Repositório cobre só
persistência; decisão de transição (approve/reject/merge) continua no
service, que compõe `TaskRepository.add` na aprovação.

R13/R14 como de costume: ``workspace_id`` sempre no predicado; não
commita.

Uso::

    repo = TaskSuggestionRepository(session)
    pending = await repo.list_by_status(ws_id, "pending")
    sugg = await repo.get_by_id(ws_id, suggestion_id)
    await repo.add(new_suggestion)
    await session.commit()
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.task import TaskSuggestion


class TaskSuggestionRepository:
    """Single Responsibility: persistência de ``TaskSuggestion``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def list_by_status(
        self,
        workspace_id: str,
        status: Optional[str] = "pending",
    ) -> list[TaskSuggestion]:
        """Lista sugestões por status (default: ``pending``).

        Ordenação: ``created_at DESC`` — mais recentes primeiro, ideal
        para a fila de aprovação. ``status=None`` desativa o filtro
        (retorna todas do workspace).
        """
        stmt = select(TaskSuggestion).where(
            TaskSuggestion.workspace_id == workspace_id,
        )
        if status is not None:
            stmt = stmt.where(TaskSuggestion.status == status)
        stmt = stmt.order_by(TaskSuggestion.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(
        self, workspace_id: str, suggestion_id: str
    ) -> Optional[TaskSuggestion]:
        """Retorna sugestão por id dentro do workspace, ou ``None``."""
        result = await self._session.execute(
            select(TaskSuggestion).where(
                TaskSuggestion.workspace_id == workspace_id,
                TaskSuggestion.id == suggestion_id,
            )
        )
        return result.scalar_one_or_none()

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def add(
        self, suggestion: TaskSuggestion, *, flush: bool = True
    ) -> TaskSuggestion:
        """Registra ``suggestion`` na sessão. Caller commita."""
        self._session.add(suggestion)
        if flush:
            await self._session.flush()
        return suggestion

    async def save(self, suggestion: TaskSuggestion) -> TaskSuggestion:
        """Flush pós-mutation (sem commit). Útil após aprovação/rejeição
        que já atualiza campos in-place na instância.
        """
        self._session.add(suggestion)
        await self._session.flush()
        return suggestion
