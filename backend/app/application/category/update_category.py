"""Use case: atualizar categoria (partial update + replace de keywords)."""

from __future__ import annotations

from backend.app.application.base.errors import ConflictError, NotFoundError
from backend.app.application.category._protocols import CategoryRepositoryProtocol
from backend.app.schemas.dto.category import (
    CategoryResponse,
    CategoryUpdateCommand,
    category_to_response,
)


async def update_category(
    category_id: str,
    cmd: CategoryUpdateCommand,
    *,
    workspace_id: str,
    repo: CategoryRepositoryProtocol,
) -> CategoryResponse:
    """Valida unicidade do novo ``code`` (se alterado) e delega ao repo."""
    cat = await repo.get_by_id_with_keywords(workspace_id, category_id)
    if not cat:
        raise NotFoundError("Categoria não encontrada", code="category_not_found")

    updates = cmd.model_dump(exclude_unset=True)
    keywords_update = updates.pop("keywords", None)

    new_code = updates.get("code")
    if new_code is not None and new_code != cat.code:
        if await repo.code_exists(workspace_id, new_code, exclude_id=cat.id):
            raise ConflictError(
                f"Categoria com code '{new_code}' já existe",
                code="duplicate_code",
            )

    updated = await repo.update(cat, updates=updates, keywords=keywords_update)
    return category_to_response(updated)
