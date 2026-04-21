"""Protocol consumido pelos use cases de ``Category``."""

from __future__ import annotations

from typing import Optional, Protocol

from backend.app.models.category import Category


class CategoryRepositoryProtocol(Protocol):
    async def list_by_workspace(self, workspace_id: str) -> list[Category]: ...

    async def get_by_id(
        self, workspace_id: str, category_id: str
    ) -> Optional[Category]: ...

    async def get_by_id_with_keywords(
        self, workspace_id: str, category_id: str
    ) -> Optional[Category]: ...

    async def code_exists(
        self,
        workspace_id: str,
        code: str,
        *,
        exclude_id: Optional[str] = None,
    ) -> bool: ...

    async def create(
        self,
        workspace_id: str,
        *,
        code: str,
        name: str,
        category_type: str,
        monthly_cap: Optional[float] = None,
        order: int = 0,
        keywords: Optional[list[str]] = None,
    ) -> Category: ...

    async def update(
        self,
        category: Category,
        *,
        updates: dict,
        keywords: Optional[list[str]] = None,
    ) -> Category: ...

    async def delete(self, category: Category) -> None: ...
