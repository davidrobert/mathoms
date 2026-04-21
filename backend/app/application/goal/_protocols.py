"""Protocol do repo do agregado ``Goal``.

Implementado por ``backend.app.repositories.goal_repository.GoalRepository``
(produção) e ``backend.tests.fakes.goal.FakeGoalRepository`` (testes),
via duck typing.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional, Protocol

from backend.app.models.goal import Goal


class GoalRepositoryProtocol(Protocol):
    async def get_active_by_type(
        self, workspace_id: str, goal_type: str
    ) -> Optional[Goal]: ...

    async def get_by_id(
        self, workspace_id: str, goal_id: str
    ) -> Optional[Goal]: ...

    async def list_by_workspace_and_type(
        self, workspace_id: str, goal_type: str
    ) -> list[Goal]: ...

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
    ) -> Goal: ...
