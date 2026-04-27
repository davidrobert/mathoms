"""Protocol do DecisionRepository — DIP (ADR-101).

Use cases dependem do protocol; testes injetam fake (``FakeDecisionRepository``)
sem montar SQLAlchemy. Implementação concreta: ``DecisionRepository``.
"""

from __future__ import annotations

from typing import Optional, Protocol

from backend.app.models.decision import Decision, DecisionEvent


class DecisionRepositoryProtocol(Protocol):
    async def get_by_id(
        self, workspace_id: str, decision_id: str
    ) -> Optional[Decision]: ...

    async def get_by_code(
        self, workspace_id: str, code: str
    ) -> Optional[Decision]: ...

    async def list_by_workspace(self, workspace_id: str) -> list[Decision]: ...

    async def list_events(self, decision_id: str) -> list[DecisionEvent]: ...

    async def add(self, decision: Decision) -> Decision: ...

    async def add_event(self, event: DecisionEvent) -> DecisionEvent: ...
