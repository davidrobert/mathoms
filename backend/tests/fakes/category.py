"""Fake in-memory do ``CategoryRepository``.

Implementa ``backend.app.application.category._protocols.CategoryRepositoryProtocol``
suficiente para rodar os use cases sem DB.
"""

from __future__ import annotations

import uuid
from typing import Optional

from backend.app.models.category import Category, CategoryKeyword


class FakeCategoryRepository:
    def __init__(self) -> None:
        self._cats: dict[str, Category] = {}

    async def list_by_workspace(self, workspace_id: str) -> list[Category]:
        cats = [c for c in self._cats.values() if c.workspace_id == workspace_id]
        cats.sort(key=lambda c: (c.order, c.code))
        return cats

    async def get_by_id(self, workspace_id: str, category_id: str) -> Optional[Category]:
        c = self._cats.get(category_id)
        if c is None or c.workspace_id != workspace_id:
            return None
        return c

    async def get_by_id_with_keywords(
        self, workspace_id: str, category_id: str
    ) -> Optional[Category]:
        return await self.get_by_id(workspace_id, category_id)

    async def code_exists(
        self,
        workspace_id: str,
        code: str,
        *,
        exclude_id: Optional[str] = None,
    ) -> bool:
        for c in self._cats.values():
            if c.workspace_id != workspace_id or c.code != code:
                continue
            if exclude_id is not None and c.id == exclude_id:
                continue
            return True
        return False

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
    ) -> Category:
        cat = Category(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            code=code,
            name=name,
            category_type=category_type,
            monthly_cap=monthly_cap,
            order=order,
        )
        cat.keywords = [
            CategoryKeyword(id=str(uuid.uuid4()), category_id=cat.id, keyword=kw)
            for kw in (keywords or [])
        ]
        self._cats[cat.id] = cat
        return cat

    async def update(
        self,
        category: Category,
        *,
        updates: dict,
        keywords: Optional[list[str]] = None,
    ) -> Category:
        for field, value in updates.items():
            setattr(category, field, value)
        if keywords is not None:
            category.keywords = [
                CategoryKeyword(id=str(uuid.uuid4()), category_id=category.id, keyword=kw)
                for kw in keywords
            ]
        return category

    async def delete(self, category: Category) -> None:
        self._cats.pop(category.id, None)
