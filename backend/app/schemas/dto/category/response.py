"""Response DTOs do agregado ``Category``.

Wire shape retornado pela API — mudanças aqui são **breaking** para o
frontend (`lib/api.ts` / tela de edição de categorias). Compat binária com
``schemas.config.CategorySchema`` é preservada durante A6e; o tipo legado
re-exporta estes durante a janela de transição.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    """Categoria de classificação com suas keywords."""

    id: Optional[str] = None
    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código canônico único no workspace (ex.: 'moradia', 'receita_pj').",
    )
    name: str = Field(..., min_length=1, max_length=100)
    category_type: str = Field(
        ...,
        pattern=r"^(expense|income)$",
        description="Tipo — 'expense' (despesa) ou 'income' (receita).",
    )
    monthly_cap: Optional[float] = Field(
        None, ge=0, description="Teto mensal de gasto (alertas de orçamento)."
    )
    order: int = Field(default=0, ge=0)
    keywords: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    """Wrapper para ``GET /categories``; carrega versão de template usada vs. latest (ADR-185 §4)."""

    # ``template_version_used`` / ``latest_template_version`` são metadados da
    # resolução (não da entidade), por isso moram no wire-shape e não no
    # domain ``ResolvedCategory``. UI sinaliza v desatualizada quando
    # ``used < latest`` (sem CTA, só visual — W4).
    categories: list[CategoryResponse]
    total: int
    template_version_used: int = Field(
        default=1,
        ge=1,
        description="Versão do template ativa para esta resolução.",
    )
    latest_template_version: int = Field(
        default=1,
        ge=1,
        description=(
            "Maior ``template_version`` em ``category_templates``. "
            "Quando ``template_version_used < latest_template_version`` a UI "
            "mostra sinal de v desatualizada (sem CTA)."
        ),
    )
