"""Repository SQLAlchemy async para `PropertyIdentity` + `WorkspacePropertyOverride` (ADR-215 P4)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    PropertyIdentity,
    Workspace,
    WorkspacePropertyOverride,
)


class PropertyRepository:
    """Async repo para os 2 aggregates de imóvel (ADR-215)."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_identities(self, workspace_id: str) -> list[PropertyIdentity]:
        """Lista todas as `property_identity` rows do workspace."""
        result = await self._db.execute(
            select(PropertyIdentity)
            .where(PropertyIdentity.workspace_id == workspace_id)
            .order_by(PropertyIdentity.first_seen_year.desc(), PropertyIdentity.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_identity(self, workspace_id: str, property_id: str) -> Optional[PropertyIdentity]:
        result = await self._db.execute(
            select(PropertyIdentity).where(
                PropertyIdentity.id == property_id,
                PropertyIdentity.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_overrides(self, workspace_id: str) -> dict[str, WorkspacePropertyOverride]:
        """Map `property_id → override` para todos os overrides do workspace."""
        result = await self._db.execute(
            select(WorkspacePropertyOverride).where(
                WorkspacePropertyOverride.workspace_id == workspace_id
            )
        )
        return {o.property_id: o for o in result.scalars().all()}

    async def upsert_override(
        self,
        *,
        workspace_id: str,
        property_id: str,
        classification: str,
        override_source: str,
        created_by_user_id: Optional[str],
    ) -> WorkspacePropertyOverride:
        """Cria ou atualiza override (idempotente). Retorna a row final."""
        existing = await self._db.execute(
            select(WorkspacePropertyOverride).where(
                WorkspacePropertyOverride.workspace_id == workspace_id,
                WorkspacePropertyOverride.property_id == property_id,
            )
        )
        row = existing.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if row is None:
            row = WorkspacePropertyOverride(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                property_id=property_id,
                classification=classification,
                override_source=override_source,
                created_by_user_id=created_by_user_id,
                created_at=now,
                updated_at=now,
            )
            self._db.add(row)
        else:
            row.classification = classification
            row.override_source = override_source
            row.updated_at = now
        await self._db.flush()
        return row

    async def delete_overrides_with_classification(
        self,
        workspace_id: str,
        classification: str,
    ) -> int:
        """Remove todos overrides com determinada classification no workspace."""
        result = await self._db.execute(
            delete(WorkspacePropertyOverride).where(
                WorkspacePropertyOverride.workspace_id == workspace_id,
                WorkspacePropertyOverride.classification == classification,
            )
        )
        return int(result.rowcount or 0)

    async def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        result = await self._db.execute(select(Workspace).where(Workspace.id == workspace_id))
        return result.scalar_one_or_none()
