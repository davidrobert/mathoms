"""Use case: listar categorias do workspace (fallback para defaults globais)."""

from __future__ import annotations

from typing import Any

from backend.app.application.category._protocols import CategoryRepositoryProtocol
from backend.app.schemas.dto.category import (
    CategoryListResponse,
    category_to_response,
    convert_global_defaults_to_responses,
    count_defaults,
)


async def list_categories(
    workspace_id: str,
    *,
    repo: CategoryRepositoryProtocol,
    global_defaults: dict[str, Any] | None = None,
) -> CategoryListResponse:
    """Se o workspace tem categorias, retorna-as; senão, devolve defaults."""
    cats = await repo.list_by_workspace(workspace_id)
    if cats:
        responses = [category_to_response(c) for c in cats]
        return CategoryListResponse(categories=responses, total=len(responses))

    defaults = global_defaults or {}
    return CategoryListResponse(
        categories=convert_global_defaults_to_responses(defaults),
        total=count_defaults(defaults),
    )
