"""GoalRepository — CRUD async para o agregado ``Goal`` (versionado).

O modelo ``Goal`` é **imutável por versão** (ADR-073): cada edição cria
uma nova row com ``effective_from = hoje`` e fecha a anterior com
``effective_to = ontem``. A "versão vigente" é aquela com
``effective_to IS NULL`` — garantida única por ``(workspace_id, type)``
pelo unique index parcial ``ux_goals_current_ws_type``.

Este repositório expõe as duas visões desse modelo:

- ``get_active_by_type``: a versão vigente (se existir).
- ``list_by_workspace_and_type``: histórico completo ordenado
  cronologicamente (mais recente primeiro).
- ``create_new_version``: atômico ``close(active) + insert(new)`` —
  única forma correta de criar uma versão nova.

R13 (ADR-101): toda query inclui ``workspace_id`` no predicado —
multi-tenancy é invariante. R14: repo **não commita** — caller é dono
do boundary transacional. ``create_new_version`` faz ``flush`` para
resolver o unique index contra a transação atual antes do insert novo.

Escopo A6e.6: este repositório cobre **persistência de Goal** e nada
mais. Compute services (``compute_if_derived``, etc.) permanecem em
``goal_service.py`` por design — são domain logic pura e não têm
dependência de DB.

Uso::

    repo = GoalRepository(session)
    goal = await repo.get_active_by_type(ws_id, "INDEPENDENCIA_FINANCEIRA")
    hist = await repo.list_by_workspace_and_type(ws_id, "APORTE_MENSAL")
    new_goal = await repo.create_new_version(
        ws_id, "INDEPENDENCIA_FINANCEIRA",
        params_json={...}, derived_json={...},
        created_by=user_id, notes="revisão anual",
    )
    await session.commit()
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.goal import VALID_GOAL_TYPES, Goal


class GoalRepository:
    """Single Responsibility: persistência do agregado ``Goal``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def get_active_by_type(self, workspace_id: str, goal_type: str) -> Optional[Goal]:
        """Retorna a versão vigente para ``(workspace_id, goal_type)``.

        Vigente = ``effective_to IS NULL``. Pelo unique index parcial
        ``ux_goals_current_ws_type``, há no máximo uma.
        """
        if goal_type not in VALID_GOAL_TYPES:
            raise ValueError(f"Tipo de goal inválido: {goal_type}")

        result = await self._session.execute(
            select(Goal).where(
                Goal.workspace_id == workspace_id,
                Goal.type == goal_type,
                Goal.effective_to.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, workspace_id: str, goal_id: str) -> Optional[Goal]:
        """Retorna goal por id dentro do workspace (qualquer versão, ou ``None``)."""
        result = await self._session.execute(
            select(Goal).where(
                Goal.id == goal_id,
                Goal.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace_and_type(self, workspace_id: str, goal_type: str) -> list[Goal]:
        """Histórico completo do tipo, mais recente primeiro.

        Ordenação: ``effective_from DESC`` — a vigente é sempre a
        primeira (mesmo que haja só ela).
        """
        if goal_type not in VALID_GOAL_TYPES:
            raise ValueError(f"Tipo de goal inválido: {goal_type}")

        result = await self._session.execute(
            select(Goal)
            .where(
                Goal.workspace_id == workspace_id,
                Goal.type == goal_type,
            )
            .order_by(Goal.effective_from.desc())
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def create_new_version(
        self,
        workspace_id: str,
        goal_type: str,
        *,
        params_json: dict[str, Any],
        derived_json: dict[str, Any],
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
        is_template: bool = False,
        effective_from: Optional[date] = None,
    ) -> Goal:
        """Cria nova versão — fecha a vigente (se existir) na mesma transação.

        Semântica append-only (ADR-073):

        - Se existir vigente (``effective_to IS NULL``) para o
          ``(workspace_id, goal_type)``, fecha-a com
          ``effective_to = effective_from - 1 dia``.
        - Flush intermediário resolve o unique index parcial
          ``ux_goals_current_ws_type`` antes do insert novo — sem isso,
          o INSERT quebraria com ``IntegrityError``.
        - Insere o registro novo com ``effective_to = None``.

        **Não commita** — caller é dono do boundary transacional. O
        caller passa ``params_json`` e ``derived_json`` já serializados
        (repo não conhece Pydantic nem compute services).
        """
        if goal_type not in VALID_GOAL_TYPES:
            raise ValueError(f"Tipo de goal inválido: {goal_type}")

        eff_from = effective_from or date.today()

        current = await self.get_active_by_type(workspace_id, goal_type)
        if current is not None:
            current.effective_to = eff_from - timedelta(days=1)
            self._session.add(current)
            await self._session.flush()

        goal = Goal(
            workspace_id=workspace_id,
            type=goal_type,
            params_json=params_json,
            derived_json=derived_json,
            effective_from=eff_from,
            effective_to=None,
            created_by=created_by,
            notes=notes,
            is_template=is_template,
        )
        self._session.add(goal)
        await self._session.flush()
        return goal
