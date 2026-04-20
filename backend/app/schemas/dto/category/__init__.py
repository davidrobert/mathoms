"""DTOs do agregado ``Category`` (inclui ``CategoryKeyword`` como sub-entidade).

Re-exports convenientes — prefira estes imports ao invés de alcançar módulos
internos, para manter o pacote como fronteira do agregado.
"""

from backend.app.schemas.dto.category.command import (
    CategoryCreateCommand,
    CategoryUpdateCommand,
)
from backend.app.schemas.dto.category.mapper import (
    category_to_response,
    convert_global_defaults_to_responses,
    count_defaults,
)
from backend.app.schemas.dto.category.response import (
    CategoryListResponse,
    CategoryResponse,
)

__all__ = [
    "CategoryCreateCommand",
    "CategoryListResponse",
    "CategoryResponse",
    "CategoryUpdateCommand",
    "category_to_response",
    "convert_global_defaults_to_responses",
    "count_defaults",
]
