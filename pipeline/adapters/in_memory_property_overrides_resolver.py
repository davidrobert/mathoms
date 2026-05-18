"""`InMemoryPropertyOverridesResolver` — implementação para testes (ADR-215 P3)."""

from __future__ import annotations


class InMemoryPropertyOverridesResolver:
    """Resolver in-memory para testes — fixture `{workspace_id: {property_id: classification}}`."""

    def __init__(self, overrides_by_workspace: dict[str, dict[str, str]] | None = None) -> None:
        self._data = overrides_by_workspace or {}

    def list_for_workspace(self, workspace_id: str) -> dict[str, str]:
        return dict(self._data.get(workspace_id, {}))

    def set(self, workspace_id: str, property_id: str, classification: str) -> None:
        self._data.setdefault(workspace_id, {})[property_id] = classification
