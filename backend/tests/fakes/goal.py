"""Fake in-memory do ``GoalRepository``.

Replica a regra de append-only: ``create_new_version`` fecha a versão
vigente (se existir) antes de inserir a nova — mesma semântica do repo
SQLAlchemy real (ADR-073).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from backend.app.models.goal import VALID_GOAL_TYPES, Goal


class FakeGoalRepository:
    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}
        self._insertion_counter = 0  # garante tiebreak estável no histórico

    async def get_active_by_type(
        self, workspace_id: str, goal_type: str
    ) -> Optional[Goal]:
        if goal_type not in VALID_GOAL_TYPES:
            raise ValueError(f"Tipo de goal inválido: {goal_type}")
        for g in self._goals.values():
            if (
                g.workspace_id == workspace_id
                and g.type == goal_type
                and g.effective_to is None
            ):
                return g
        return None

    async def get_by_id(
        self, workspace_id: str, goal_id: str
    ) -> Optional[Goal]:
        g = self._goals.get(goal_id)
        if g is None or g.workspace_id != workspace_id:
            return None
        return g

    async def list_by_workspace_and_type(
        self, workspace_id: str, goal_type: str
    ) -> list[Goal]:
        if goal_type not in VALID_GOAL_TYPES:
            raise ValueError(f"Tipo de goal inválido: {goal_type}")
        goals = [
            g for g in self._goals.values()
            if g.workspace_id == workspace_id and g.type == goal_type
        ]
        # Desempate por ordem de inserção quando ``effective_from`` coincide
        # (2 versões no mesmo dia) — evita ordem não-determinística.
        goals.sort(
            key=lambda g: (g.effective_from, getattr(g, "_fake_insert_order", 0)),
            reverse=True,
        )
        return goals

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
        if goal_type not in VALID_GOAL_TYPES:
            raise ValueError(f"Tipo de goal inválido: {goal_type}")

        eff_from = effective_from or date.today()
        current = await self.get_active_by_type(workspace_id, goal_type)
        if current is not None:
            current.effective_to = eff_from - timedelta(days=1)

        now = datetime.now(timezone.utc)
        goal = Goal(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            type=goal_type,
            params_json=params_json,
            derived_json=derived_json,
            effective_from=eff_from,
            effective_to=None,
            created_by=created_by,
            notes=notes,
            is_template=is_template,
            created_at=now,
            updated_at=now,
        )
        self._insertion_counter += 1
        goal._fake_insert_order = self._insertion_counter  # type: ignore[attr-defined]
        self._goals[goal.id] = goal
        return goal
