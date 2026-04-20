"""Mapper ORM → DTO + helpers de fallback para o agregado ``Category``.

Responsabilidades:

1. ``category_to_response``: converte o ORM ``Category`` (com ``keywords``
   eager-loaded) em ``CategoryResponse``.
2. ``convert_global_defaults_to_responses``: converte o fallback global
   ``config/categorization.json`` (shape ``{expense_keywords, income_keywords}``)
   para lista de DTOs — usado quando o workspace ainda não tem categorias
   persistidas no DB.

O mapper **não** recebe ``AsyncSession``. Recebe a instância ORM já
hidratada — isso torna o mapper testável sem DB.
"""

from __future__ import annotations

from typing import Any

from backend.app.models.category import Category
from backend.app.schemas.dto.category.response import CategoryResponse


def category_to_response(category: Category) -> CategoryResponse:
    """Converte ORM ``Category`` → DTO de resposta.

    Pré-condição: ``category.keywords`` deve estar eager-loaded. Se não
    estiver, SQLAlchemy lança ``MissingGreenlet`` em contexto async —
    mapper **não** tenta recarregar (não tem session).

    A ordem das keywords vem do ``order_by`` definido em
    ``Category.keywords`` relationship (``CategoryKeyword.id``).
    """
    keywords = [kw.keyword for kw in category.keywords] if category.keywords else []
    return CategoryResponse(
        id=category.id,
        code=category.code,
        name=category.name,
        category_type=category.category_type,
        monthly_cap=category.monthly_cap,
        order=category.order,
        keywords=keywords,
    )


def convert_global_defaults_to_responses(
    data: dict[str, Any],
) -> list[CategoryResponse]:
    """Converte ``config/categorization.json`` global → lista de DTOs.

    Shape esperado (paridade com helper legado
    ``_convert_categorization_json_to_schemas``)::

        {
            "expense_keywords": {"moradia": ["aluguel", "iptu"], ...},
            "income_keywords":  {"receita_pj": ["salario", ...], ...}
        }

    Regras de derivação:

    - ``code`` vem da chave do dict.
    - ``name`` vem de ``code.replace("_", " ").title()`` (ex.: ``receita_pj``
      → ``Receita Pj``).
    - ``category_type`` vem da seção (``expense`` ou ``income``).
    - ``order`` é sequencial começando por expense e continuando em income.
    - Categorias default não têm ``id`` (ainda não persistidas) nem
      ``monthly_cap``.
    """
    responses: list[CategoryResponse] = []
    order = 0
    for cat_type, key in (
        ("expense", "expense_keywords"),
        ("income", "income_keywords"),
    ):
        section = data.get(key, {}) or {}
        for code, keywords in section.items():
            responses.append(
                CategoryResponse(
                    code=code,
                    name=code.replace("_", " ").title(),
                    category_type=cat_type,
                    order=order,
                    keywords=list(keywords or []),
                )
            )
            order += 1
    return responses


def count_defaults(data: dict[str, Any]) -> int:
    """Total de categorias no fallback (expense + income).

    Usado pela API para popular ``CategoryListResponse.total`` quando o
    workspace está usando os defaults (paridade com comportamento legado:
    ``len(expense_keywords) + len(income_keywords)``).
    """
    expense = data.get("expense_keywords", {}) or {}
    income = data.get("income_keywords", {}) or {}
    return len(expense) + len(income)
