"""Protocol do `ProtectionRepository` (ADR-101 DIP)."""

from __future__ import annotations

from typing import Optional, Protocol

from backend.app.models.protection import Protection


class ProtectionRepositoryProtocol(Protocol):
    async def get_by_id(self, workspace_id: str, protection_id: str) -> Optional[Protection]: ...

    async def list_by_workspace(self, workspace_id: str) -> list[Protection]: ...

    async def list_active_by_workspace(self, workspace_id: str) -> list[Protection]: ...

    async def add(self, protection: Protection) -> Protection: ...
