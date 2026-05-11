"""``WorkspaceCategoryOverride`` async CRUD (ADR-137 · A7.3 · A11.W1) — thin; service orquestra commit/cache."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.category_template import WorkspaceCategoryOverride


class WorkspaceCategoryOverrideRepository:
    """Async repository — workspace-scoped CRUD do override."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_workspace(self, workspace_id: str) -> list[WorkspaceCategoryOverride]:
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
        updated_by_user_id: Optional[str] = None,
    ) -> WorkspaceCategoryOverride:
        """Insere/atualiza override; ``updated_by_user_id`` populado quando caller tem ``current_user`` (audit ADR-185 §4)."""
        existing = await self.get_by_template_key(workspace_id, template_key)
        target = existing or WorkspaceCategoryOverride(
            workspace_id=workspace_id, template_key=template_key
        )
        target.label_override = label_override
        target.keywords_override = keywords_override
        target.monthly_cap_brl_cents_override = monthly_cap_brl_cents_override
        target.disabled = disabled
        if updated_by_user_id is not None:
            target.updated_by_user_id = updated_by_user_id
        if existing is None:
            self._session.add(target)
        await self._session.flush()
        return target

    async def delete(self, override: WorkspaceCategoryOverride) -> None:
        """Apaga override → workspace volta ao default do template. Caller comita."""
        await self._session.delete(override)
        await self._session.flush()

    async def delete_all_in_workspace(self, workspace_id: str) -> int:
        """Apaga todos os overrides do workspace; thin (flush, sem commit). Orquestração em ``CategoryOverrideService.reset_all``."""
        rows = await self.list_by_workspace(workspace_id)
        for row in rows:
            await self._session.delete(row)
        await self._session.flush()
        return len(rows)
