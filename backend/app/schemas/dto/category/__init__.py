"""DTOs do agregado ``Category`` (inclui ``CategoryKeyword`` como sub-entidade).

Re-exports convenientes — prefira estes imports ao invés de alcançar módulos
internos, para manter o pacote como fronteira do agregado. Wire servido pelo
caminho de overrides (``/config/category-overrides/*``, ADR-137); o CRUD
legado ``/config/categories`` foi removido em A12.cat-legacy-sunset.
"""

from backend.app.schemas.dto.category.command import CategoryUpdateCommand
from backend.app.schemas.dto.category.response import (
    CategoryListResponse,
    CategoryResponse,
)

__all__ = [
    "CategoryListResponse",
    "CategoryResponse",
    "CategoryUpdateCommand",
]
