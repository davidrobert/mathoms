"""Command DTOs (inputs de write) do agregado ``Category``.

Um *command* é a representação de uma **intenção** do caller. Pós-sunset do
CRUD legado ``/config/categories`` (A12.cat-legacy-sunset), o único write é
o upsert de override (``PUT /config/category-overrides/{template_key}``,
ADR-137/ADR-185) — o command vira diff contra o template global.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CategoryUpdateCommand(BaseModel):
    """Input do ``PUT /category-overrides/{template_key}`` (partial update).

    Campos iguais ao valor do template não geram override (diff-only).
    ``monthly_cap`` chega em BRL float no wire e é persistido como cents
    (``monthly_cap_brl_cents``) pelo use case.

    Para ``keywords``:

    - ``None`` / ausente → não altera a lista existente.
    - ``[]`` → **apaga** todas as keywords.
    - lista com itens → **substitui** a lista inteira pelos itens novos.
    """

    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category_type: Optional[str] = Field(None, pattern=r"^(expense|income)$")
    monthly_cap: Optional[float] = Field(None, ge=0)
    order: Optional[int] = Field(None, ge=0)
    keywords: Optional[list[str]] = None
