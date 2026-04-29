"""Protocols dos repositórios usados pelos use cases de Suggestion (ADR-153).

Use cases dependem dos protocols; testes injetam fakes
(``FakeSuggestionRepository`` etc.) sem montar SQLAlchemy.
"""

from __future__ import annotations

from typing import Optional, Protocol, Sequence

from backend.app.models.suggestion import Suggestion


class SuggestionRepositoryProtocol(Protocol):
    async def get_by_id(
        self, workspace_id: str, suggestion_id: str
    ) -> Optional[Suggestion]: ...

    async def get_by_dedup_key(
        self,
        workspace_id: str,
        dedup_key: str,
        statuses: Optional[Sequence[str]] = None,
    ) -> list[Suggestion]: ...

    async def list_by_workspace(
        self, workspace_id: str, status: Optional[str] = None
    ) -> list[Suggestion]: ...

    async def count_by_workspace(
        self, workspace_id: str, status: Optional[str] = None
    ) -> int: ...

    async def add(self, suggestion: Suggestion) -> Suggestion: ...
