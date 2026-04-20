"""Command DTOs (inputs de write) do agregado ``Category``.

Um *command* é a representação de uma **intenção** do caller (criar,
atualizar, apagar). É validado na camada de transporte antes de chegar ao
use case.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreateCommand(BaseModel):
    """Input do ``POST /categories``."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    category_type: str = Field(..., pattern=r"^(expense|income)$")
    monthly_cap: Optional[float] = Field(None, ge=0)
    order: int = Field(default=0, ge=0)
    keywords: list[str] = Field(default_factory=list)


class CategoryUpdateCommand(BaseModel):
    """Input do ``PUT /categories/{id}`` — campos opcionais (partial update).

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
