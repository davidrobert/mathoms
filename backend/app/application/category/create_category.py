"""Use case: criar categoria (valida unicidade de ``code``)."""

from __future__ import annotations

from backend.app.application.base.errors import ConflictError
from backend.app.application.category._protocols import CategoryRepositoryProtocol
from backend.app.schemas.dto.category import (
    CategoryCreateCommand,
    CategoryResponse,
    category_to_response,
)


async def create_category(
    cmd: CategoryCreateCommand,
    *,
    workspace_id: str,
    repo: CategoryRepositoryProtocol,
) -> CategoryResponse:
    """409 se ``code`` já existe; senão cria com as keywords embutidas."""
    if await repo.code_exists(workspace_id, cmd.code):
        raise ConflictError(
            f"Categoria com code '{cmd.code}' já existe",
            code="duplicate_code",
        )
    cat = await repo.create(
        workspace_id,
        code=cmd.code,
        name=cmd.name,
        category_type=cmd.category_type,
        monthly_cap=cmd.monthly_cap,
        order=cmd.order,
        keywords=cmd.keywords,
    )
    return category_to_response(cat)
