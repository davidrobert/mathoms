"""ArtifactStore — abstração de I/O para artefatos do pipeline (ADR-083).

Define o protocolo e a implementação em-memória usada por testes unitários,
mantendo a fronteira arquitetural de ``pipeline/`` (sem fastapi/celery/sqlalchemy
— ver ``dev/check_pipeline_boundaries.py``):

- :class:`InMemoryArtifactStore` — sem disco, sem banco; obrigatória para testes
  unitários de domain services e goldens de execução.

A implementação de produção, ``DBArtifactStore``, vive em
``backend/app/services/db_artifact_store.py`` porque depende de SQLAlchemy
(orm layer do app web) e é exclusiva do caminho Celery+DB.

**ADR-212 PR3b:** ``DiskArtifactStore`` foi removido. Pipeline roda
exclusivamente via Celery worker com ``DBArtifactStore``; testes usam
``InMemoryArtifactStore``. **ADR-213:** ``_STAGE_TO_DIR`` + ``stage_dir_name()``
deletados (dead code sem caller runtime); ``_STAGE_TO_SUFFIX`` +
``stage_suffix()`` permanecem com 3 consumidores legítimos
(``e3_reconciler_adapter``, ``e4_categorizer_adapter``,
``e3_serialization.generate_legacy_filename``).

Durante as Fases 1-8, as chaves de stage são os nomes legados (``"E2"``,
``"E3"``, ``"E5"``...). A Fase 9 migra para nomes descritivos
(``"extract_statements"``, ``"reconcile_transactions"``...).

Exemplo (teste de domínio):

    >>> store = InMemoryArtifactStore()
    >>> store.seed("E4", "despesas", {"total": 1000})
    >>> service.run(store)
    >>> store.read("E5", "analise_financeira")
    {...}
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

# =============================================================================
# Mapeamento stage → sufixo de filename
# =============================================================================
#
# ADR-212 PR3b removeu ``DiskArtifactStore``; ADR-213 removeu
# ``_STAGE_TO_DIR`` + ``stage_dir_name()`` (dead code sem caller runtime).
# ``_STAGE_TO_SUFFIX`` permanece — consumidores documentados em
# CLAUDE.md §"Convenções de naming de artefatos".

_STAGE_TO_SUFFIX: dict[str, str] = {
    "E1": "-1b_unified.json",  # ADR-127
    "extract_members": "-1b_unified.json",  # F9.2 descriptive alias
    "E1.5c": "-1.5_consolidated.json",
    "consolidate_baseline": "-1.5_consolidated.json",  # F9.2 descriptive alias
    "E1.5": "-1.5_baseline.json",
    "extract_baseline": "-1.5_baseline.json",  # F9.2 descriptive alias
    "E1.5a": "-1.5a_extract.json",
    "extract_irpf_full": "-1.6_irpf_full.json",  # ADR-157
    "E2": "-2_extract.json",
    "E2-faturas": "-2_extract.json",
    "extract_invoices": "-2_extract.json",  # F9.2 descriptive alias
    "E2-extratos": "-2_extract.json",
    "extract_statements": "-2_extract.json",  # F9.2 descriptive alias
    "E2-llm": "-2_extract.json",
    "extract_with_llm": "-2_extract.json",  # F9.2 descriptive alias
    "E2-informe-aluguel": "-2_informe_aluguel.json",  # ADR-216 Onda 0.5b
    "extract_informe_aluguel": "-2_informe_aluguel.json",  # F9.2 descriptive alias
    "E2-informe-anual": "-2_informe_anual.json",  # ADR-238 A17 — alias legacy
    "extract_informes_anuais": "-2_informe_anual.json",  # ADR-238 A17 — polimórfico
    "E2-comprovante-bem": "-2_comprovante_bem.json",  # ADR-239 A18 — alias legacy
    "extract_comprovantes_bens": "-2_comprovante_bem.json",  # ADR-239 A18 — polimórfico
    "E3": "-3_reconciled.json",
    "reconcile_transactions": "-3_reconciled.json",  # F9.2 descriptive alias
    "E4": "-4_unified.json",
    "categorize_transactions": "-4_unified.json",  # F9.2 descriptive alias
    "E5": "-5_analysis.json",
    "analyze_finances": "-5_analysis.json",  # F9.2 descriptive alias
    "E5.N": "-5n_narrativas.json",
    "generate_narratives": "-5n_narrativas.json",  # F9.2 descriptive alias
    "E7": "-7_crossval.json",
    "E7-crossval": "-7_crossval.json",
    "validate_cross": "-7_crossval.json",  # F9.2 descriptive alias
    "E6-parecer": "-6_parecer.json",
    "review_finances_holistic": "-6_parecer.json",
}


def stage_suffix(stage: str) -> str:
    """Resolve o sufixo de arquivo (``-2_extract.json`` etc.) para um stage."""
    if stage not in _STAGE_TO_SUFFIX:
        raise KeyError(f"Stage '{stage}' sem mapeamento em _STAGE_TO_SUFFIX")
    return _STAGE_TO_SUFFIX[stage]


# =============================================================================
# Protocols (Interface Segregation — R9)
# =============================================================================


@runtime_checkable
class ReadableArtifactStore(Protocol):
    """Subset somente-leitura do protocolo. Útil para clientes que não escrevem."""

    def read(self, stage: str, key: str) -> Optional[dict]:
        """Retorna o conteúdo do artefato ou ``None`` se não existir."""
        ...

    def list_keys(self, stage: str) -> list[str]:
        """Lista todas as ``artifact_key`` disponíveis para o stage."""
        ...

    def exists(self, stage: str, key: str) -> bool:
        """True sse existe artefato para ``(stage, key)``."""
        ...


@runtime_checkable
class ArtifactStore(Protocol):
    """Protocolo completo (leitura + escrita) para persistência de artefatos.

    Todas as implementações devem satisfazer ``ReadableArtifactStore`` também.
    """

    def read(self, stage: str, key: str) -> Optional[dict]: ...

    def list_keys(self, stage: str) -> list[str]: ...

    def exists(self, stage: str, key: str) -> bool: ...

    def write(
        self,
        stage: str,
        key: str,
        data: dict,
        *,
        document_id: Optional[str] = None,
    ) -> None:
        """Persiste o artefato. ``document_id`` é FK opcional (só para E2-*)."""
        ...

    def delete(self, stage: str, key: str) -> None:
        """Remove artefato específico. No-op se não existir."""
        ...

    def delete_stage(self, stage: str) -> int:
        """Remove todos os artefatos do stage. Retorna a contagem removida."""
        ...


# =============================================================================
# InMemoryArtifactStore — zero I/O, para testes unitários de domínio
# =============================================================================


class InMemoryArtifactStore:
    """ArtifactStore em memória para testes unitários.

    Sem banco, sem disco. Permite testar ``ReconciliationService``,
    ``CategorizationService`` e ``FinancialAnalyzer`` em isolamento total —
    sem fixtures de arquivo, sem DB.

    Uso:

        >>> store = InMemoryArtifactStore()
        >>> store.seed("E4", "despesas", {"total": 100})
        >>> store.read("E4", "despesas")
        {'total': 100}
    """

    def __init__(self) -> None:
        self._data: dict[tuple[str, str], dict] = {}
        self._document_ids: dict[tuple[str, str], Optional[str]] = {}

    def read(self, stage: str, key: str) -> Optional[dict]:
        return self._data.get((stage, key))

    def list_keys(self, stage: str) -> list[str]:
        return sorted(k for s, k in self._data if s == stage)

    def exists(self, stage: str, key: str) -> bool:
        return (stage, key) in self._data

    def write(
        self,
        stage: str,
        key: str,
        data: dict,
        *,
        document_id: Optional[str] = None,
    ) -> None:
        self._data[(stage, key)] = data
        self._document_ids[(stage, key)] = document_id

    def delete(self, stage: str, key: str) -> None:
        self._data.pop((stage, key), None)
        self._document_ids.pop((stage, key), None)

    def delete_stage(self, stage: str) -> int:
        to_delete = [k for k in self._data if k[0] == stage]
        for k in to_delete:
            del self._data[k]
            self._document_ids.pop(k, None)
        return len(to_delete)

    def seed(
        self,
        stage: str,
        key: str,
        data: dict,
        *,
        document_id: Optional[str] = None,
    ) -> "InMemoryArtifactStore":
        """Fluent builder para setup de fixtures em testes."""
        self.write(stage, key, data, document_id=document_id)
        return self

    def document_id_for(self, stage: str, key: str) -> Optional[str]:
        """Expõe ``document_id`` armazenado — útil para assertions em testes."""
        return self._document_ids.get((stage, key))
