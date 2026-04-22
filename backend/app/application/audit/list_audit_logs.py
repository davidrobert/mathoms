"""Use case: lista audit logs recentes de um workspace."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from pydantic import BaseModel

from backend.app.application.audit._protocols import AuditLogRepositoryProtocol
from backend.app.models.audit_log import AuditLog


class AuditLogEntry(BaseModel):
    id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int


async def list_audit_logs(
    workspace_id: str,
    *,
    repo: AuditLogRepositoryProtocol,
    limit: int = 100,
    action: Optional[str] = None,
) -> AuditLogListResponse:
    entries = await repo.list_recent(workspace_id, limit=limit, action=action)
    return _to_response(entries)


def _to_response(entries: Sequence[AuditLog]) -> AuditLogListResponse:
    return AuditLogListResponse(
        entries=[AuditLogEntry.model_validate(e) for e in entries],
        total=len(entries),
    )
