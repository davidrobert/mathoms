"""Adapter DB do ``InstitutionCatalogProvider`` (A33.l8 · ADR-137).

Implementação concreta do protocol definido no consumer
(``pipeline/llm/institution_catalog.py`` — pipeline não importa sqlalchemy);
leitura via ``institution_resolver`` (cache Redis TTL 30d, falha aberta para
DB). Injetada em ``WorkspaceContext.institution_catalog_provider`` por
``run_context_factory`` — mesmo padrão dos resolvers ADR-215/219.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.services.institution_resolver import resolve_institutions
from pipeline.llm.institution_catalog import InstitutionEntry


class DBInstitutionCatalogProvider:
    """Lê o catálogo global ``institution_catalog`` para injection nos prompts LLM."""

    def __init__(self, *, session: Session):
        self._session = session

    def list_institutions(self) -> list[InstitutionEntry]:
        catalog = resolve_institutions(self._session)
        return [
            InstitutionEntry(
                code=inst.code,
                name=inst.name,
                category=str(inst.metadata.get("category") or "bank"),
            )
            for inst in catalog.institutions.values()
        ]
