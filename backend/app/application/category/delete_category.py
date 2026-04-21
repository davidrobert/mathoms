"""Use case: deletar categoria (cascade de keywords no repo)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.category._protocols import CategoryRepositoryProtocol


async def delete_category(
    category_id: str,
    *,
    workspace_id: str,
    repo: CategoryRepositoryProtocol,
) -> None:
    cat = await repo.get_by_id(workspace_id, category_id)
    if not cat:
        raise NotFoundError("Categoria não encontrada", code="category_not_found")
    await repo.delete(cat)
