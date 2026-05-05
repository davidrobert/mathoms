"""ArtifactStore — abstração de I/O para artefatos do pipeline (ADR-083).

Define o protocolo e duas implementações sem dependência de banco, mantendo a
fronteira arquitetural de ``pipeline/`` (sem fastapi/celery/sqlalchemy — ver
``dev/check_pipeline_boundaries.py``):

- :class:`DiskArtifactStore` — backward compat com ``processed/*.json``; usado
  pelo CLI dev e pelas Fases 1-3 antes do cutover para banco.
- :class:`InMemoryArtifactStore` — sem disco, sem banco; obrigatória para testes
  unitários de domain services.

A terceira implementação, ``DBArtifactStore``, vive em
``backend/app/services/db_artifact_store.py`` porque depende de SQLAlchemy
(orm layer do app web) e é exclusiva do caminho Celery+DB.

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

import json
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

# =============================================================================
# Mapeamentos stage → diretório/sufixo (convenção atual do ``processed/``)
# =============================================================================
#
# Fonte de verdade para ``DiskArtifactStore``.
# As chaves são os identificadores legados — Fase 9 migra para os descritivos.
#
# Invariante (testado em ``tests/pipeline/test_artifact_stores.py``):
#   todo stage listado em ``StageSpec.reads`` ou ``StageSpec.writes`` que
#   produz artefato em disco DEVE ter entrada aqui.

_STAGE_TO_DIR: dict[str, str] = {
    "E1": "members",  # members-1b_unified.json — ADR-127
    "E1.5c": "E2_extracts",  # baseline vive em E2_extracts (convenção aceita)
    "E1.5": "E2_extracts",  # baseline bruto também
    "E1.5a": "E2_extracts",  # extrato per-IRPF (1 arquivo por documento)
    "extract_irpf_full": "E2_extracts",  # E1.6 — IRPF completo (ADR-157)
    "E2": "E2_extracts",  # extratos + faturas compartilham pasta
    "E2-faturas": "E2_extracts",
    "E2-extratos": "E2_extracts",
    "E2-llm": "E2_extracts",
    "E3": "E3_reconciled",
    "E4": "E4_unified",
    "categorize_transactions": "E4_unified",  # F9.2 descriptive alias
    "E5": "E5_analysis",
    "analyze_finances": "E5_analysis",  # F9.2 descriptive alias
    "generate_narratives": "E5_analysis",  # F9.2 descriptive alias (narrativas ficam junto)
    "E5.N": "E5_analysis",  # narrativas ficam junto da análise
    "E7": "E7_review",  # crossval + review
    "E7-crossval": "E7_review",
    "E7-review": "E7_review",
    "E7-apply": "E7_review",
}

_STAGE_TO_SUFFIX: dict[str, str] = {
    "E1": "-1b_unified.json",  # ADR-127
    "E1.5c": "-1.5_consolidated.json",
    "E1.5": "-1.5_baseline.json",
    "E1.5a": "-1.5a_extract.json",
    "extract_irpf_full": "-1.6_irpf_full.json",  # ADR-157
    "E2": "-2_extract.json",
    "E2-faturas": "-2_extract.json",
    "E2-extratos": "-2_extract.json",
    "E2-llm": "-2_extract.json",
    "E3": "-3_reconciled.json",
    "E4": "-4_unified.json",
    "categorize_transactions": "-4_unified.json",  # F9.2 descriptive alias
    "E5": "-5_analysis.json",
    "analyze_finances": "-5_analysis.json",  # F9.2 descriptive alias
    "E5.N": "-5n_narrativas.json",
    "generate_narratives": "-5n_narrativas.json",  # F9.2 descriptive alias
    "E7": "-7_review.json",
    "E7-crossval": "-7_crossval.json",
    "E7-review": "-7_review.json",
    "E7-apply": "-7_apply.json",
}


def stage_dir_name(stage: str) -> str:
    """Resolve o nome de diretório sob ``processed/`` para um stage."""
    if stage not in _STAGE_TO_DIR:
        raise KeyError(f"Stage '{stage}' sem mapeamento em _STAGE_TO_DIR")
    return _STAGE_TO_DIR[stage]


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
# DiskArtifactStore — backward compat com ``processed/*.json``
# =============================================================================


class DiskArtifactStore:
    """Implementação que lê/escreve em ``<root>/processed/<stage_dir>/*<suffix>``.

    Backward-compatível com o layout atual do pipeline CLI. Chamadas de
    ``write`` criam diretórios conforme necessário; ``read`` retorna ``None``
    quando o arquivo não existe.

    O parâmetro ``document_id`` em ``write`` é ignorado (não há vínculo FK em
    disco) — preservado para compatibilidade com o protocolo.
    """

    def __init__(self, root: Path):
        self._root = Path(root).resolve()

    @property
    def processed_dir(self) -> Path:
        return self._root / "processed"

    def _stage_dir(self, stage: str) -> Path:
        return self.processed_dir / stage_dir_name(stage)

    def _path(self, stage: str, key: str) -> Path:
        return self._stage_dir(stage) / f"{key}{stage_suffix(stage)}"

    def read(self, stage: str, key: str) -> Optional[dict]:
        path = self._path(stage, key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def list_keys(self, stage: str) -> list[str]:
        stage_dir = self._stage_dir(stage)
        if not stage_dir.exists():
            return []
        suffix = stage_suffix(stage)
        keys: list[str] = []
        for f in sorted(stage_dir.iterdir()):
            name = f.name
            if name.endswith(suffix):
                keys.append(name[: -len(suffix)])
        return keys

    def exists(self, stage: str, key: str) -> bool:
        return self._path(stage, key).exists()

    def write(
        self,
        stage: str,
        key: str,
        data: dict,
        *,
        document_id: Optional[str] = None,
    ) -> None:
        path = self._path(stage, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)

    def delete(self, stage: str, key: str) -> None:
        path = self._path(stage, key)
        if path.exists():
            path.unlink()

    def delete_stage(self, stage: str) -> int:
        stage_dir = self._stage_dir(stage)
        if not stage_dir.exists():
            return 0
        suffix = stage_suffix(stage)
        count = 0
        for f in list(stage_dir.iterdir()):
            if f.name.endswith(suffix):
                f.unlink()
                count += 1
        return count


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
