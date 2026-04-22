"""AuditLogRepository — leitura paginada do log de auditoria.

Agregado somente-leitura: não expõe ``create/update/delete`` no
repositório — audit logs são imutáveis por definição (integridade).
Writes acontecem via ``audit_service.log_action(...)`` no pipeline de
ação, não aqui.
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recent(
        self,
        workspace_id: str,
        *,
        limit: int,
        action: Optional[str] = None,
    ) -> Sequence[AuditLog]:
        stmt = select(AuditLog).where(AuditLog.workspace_id == workspace_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()
