"""Protocolos de repo do agregado ``AuditLog`` (ADR-101 R15)."""

from __future__ import annotations

from typing import Optional, Protocol, Sequence

from backend.app.models.audit_log import AuditLog


class AuditLogRepositoryProtocol(Protocol):
    async def list_recent(
        self,
        workspace_id: str,
        *,
        limit: int,
        action: Optional[str] = None,
    ) -> Sequence[AuditLog]: ...
