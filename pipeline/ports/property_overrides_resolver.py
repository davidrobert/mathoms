"""`PropertyOverridesResolver` — protocolo de classificação user-driven (ADR-215 P3)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PropertyOverridesResolver(Protocol):
    """Mapping ``{property_id: classification}`` (ADR-215 §1); vazio = sem overrides."""

    def list_for_workspace(self, workspace_id: str) -> dict[str, str]: ...
