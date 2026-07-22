"""Catálogo de instituições injetado nos user prompts LLM (A33.l8 · ADR-137).

Protocol definido no consumer (``pipeline/llm``) — ``pipeline/**`` não importa
backend/sqlalchemy (gate ``check_pipeline_boundaries``); o backend injeta a
implementação concreta (``DBInstitutionCatalogProvider``) via
``WorkspaceContext.institution_catalog_provider``, no padrão dos hooks
ADR-173/ADR-307. Elimina as listas de bancos/seguradoras hardcoded nos
system prompts (``e1_members``, ``e2_llm``, ``apolice``) que driftavam do
``institution_catalog`` versionado em DB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

#: Categoria de seguradoras no ``institution_catalog`` (seed ADR-239).
INSURANCE_CATEGORY = "insurance"


@dataclass(frozen=True)
class InstitutionEntry:
    """Linha do catálogo global — ``code`` canônico + nome de exibição."""

    code: str
    name: str
    category: str = "bank"


class InstitutionCatalogProvider(Protocol):
    """Contrato injetado nos stages LLM — implementado pelo backend (ADR-137)."""

    def list_institutions(self) -> Sequence[InstitutionEntry]:
        """Catálogo global completo (leitura cacheada no adapter concreto)."""
        ...


#: Fallback determinístico (CLI isolado / testes sem provider injetado):
#: degrada explicitamente para instrução de derivação de código — nunca
#: crash, nenhum nome de instituição hardcoded no pacote de prompts.
CATALOG_UNAVAILABLE_BLOCK = (
    "(catálogo indisponível nesta execução — derive o código canônico do nome "
    'da instituição: lowercase, sem acentos e sem espaços; ex.: "Banco Exemplo" '
    "→ bancoexemplo)"
)


def render_institution_catalog(
    provider: Optional[InstitutionCatalogProvider] = None,
    *,
    include_categories: Optional[Sequence[str]] = None,
    exclude_categories: Sequence[str] = (),
) -> str:
    """Bloco de user prompt (``- codigo (Nome)`` por linha); sem provider ou catálogo
    vazio degrada p/ ``CATALOG_UNAVAILABLE_BLOCK``; erro do provider injetado propaga."""
    if provider is None:
        return CATALOG_UNAVAILABLE_BLOCK
    entries = [
        entry
        for entry in provider.list_institutions()
        if (include_categories is None or entry.category in include_categories)
        and entry.category not in exclude_categories
    ]
    if not entries:
        return CATALOG_UNAVAILABLE_BLOCK
    return "\n".join(f"- {e.code} ({e.name})" for e in sorted(entries, key=lambda e: e.code))


def institution_code_map(
    provider: Optional[InstitutionCatalogProvider] = None,
    *,
    include_categories: Optional[Sequence[str]] = None,
) -> dict[str, str]:
    """Mapping ``code → nome de exibição`` (mesmo filtro do render) — consumido
    pela canonicalização de ``seguradora`` (A37.l11); ``{}`` sem provider."""
    if provider is None:
        return {}
    return {
        e.code: e.name
        for e in provider.list_institutions()
        if include_categories is None or e.category in include_categories
    }
