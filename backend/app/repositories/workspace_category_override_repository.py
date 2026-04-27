"""Repository: ``WorkspaceCategoryOverride`` async (usado pela API CRUD A7.3 · ADR-137)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.category_template import WorkspaceCategoryOverride


class WorkspaceCategoryOverrideRepository:
    """Async repository — workspace-scoped CRUD do override."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_workspace(
        self, workspace_id: str
    ) -> list[WorkspaceCategoryOverride]:
        result = await self._session.execute(
            select(WorkspaceCategoryOverride).where(
                WorkspaceCategoryOverride.workspace_id == workspace_id
            )
        )
        return list(result.scalars().all())

    async def get_by_template_key(
        self, workspace_id: str, template_key: str
    ) -> Optional[WorkspaceCategoryOverride]:
        result = await self._session.execute(
            select(WorkspaceCategoryOverride).where(
                WorkspaceCategoryOverride.workspace_id == workspace_id,
                WorkspaceCategoryOverride.template_key == template_key,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        workspace_id: str,
        template_key: str,
        *,
        label_override: Optional[str] = None,
        keywords_override: Optional[list[str]] = None,
        monthly_cap_brl_cents_override: Optional[int] = None,
        disabled: bool = False,
    ) -> WorkspaceCategoryOverride:
        """Insere ou atualiza override; (workspace_id, template_key) é unique."""
        existing = await self.get_by_template_key(workspace_id, template_key)
        if existing is None:
            new_override = WorkspaceCategoryOverride(
                workspace_id=workspace_id,
                template_key=template_key,
                label_override=label_override,
                keywords_override=keywords_override,
                monthly_cap_brl_cents_override=monthly_cap_brl_cents_override,
                disabled=disabled,
            )
            self._session.add(new_override)
            await self._session.commit()
            await self._session.refresh(new_override)
            return new_override
        existing.label_override = label_override
        existing.keywords_override = keywords_override
        existing.monthly_cap_brl_cents_override = monthly_cap_brl_cents_override
        existing.disabled = disabled
        await self._session.commit()
        await self._session.refresh(existing)
        return existing

    async def delete(self, override: WorkspaceCategoryOverride) -> None:
        """Apagar override → workspace volta ao default do template."""
        await self._session.delete(override)
        await self._session.commit()

    async def delete_all_in_workspace(self, workspace_id: str) -> int:
        """Apaga todos os overrides do workspace (usado em testes / reset)."""
        rows = await self.list_by_workspace(workspace_id)
        for row in rows:
            await self._session.delete(row)
        await self._session.commit()
        return len(rows)
