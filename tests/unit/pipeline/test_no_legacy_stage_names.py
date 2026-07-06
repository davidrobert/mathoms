"""Guardrail: identificadores E* legados não escapam das ilhas permitidas.

Pós-F9.6 (W6-T03, 2026-07-06) **nenhum writer/label de produção emite nome
legado** — as ilhas restantes são vocabulário congelado (``STAGE_RENAME_MAP``,
``SCHEMA_BY_STAGE``, labels de lineage edge, migrations, fixtures). Este teste
garante que NOVAS menções em código não previsto viram falha de CI antes de
chegarem a produção.

**Matching (W6-T03/F9.5):** apenas *string literals* (``"E5"`` / ``'E5'``) —
identificadores de stage em código. Menções em prosa (comentários, docstrings,
mensagens de log tipo ``"E5: extracted..."``) são vocabulário de domínio
histórico e não vazam para a coluna ``pipeline_artifacts.stage``.

**Enforcement:** CI roda com ``MATHOMS_ENFORCE_STAGE_RENAME=1`` → HARD-FAIL
(ligado em W6-T03/F9.5). Sem a env var o teste skipa (dev local rápido).
"""

from __future__ import annotations

import functools
import os
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(REPO_ROOT))

from pipeline.stage_spec import STAGE_RENAME_MAP  # noqa: E402

LEGACY_NAMES = sorted(STAGE_RENAME_MAP.keys())

# Ilhas permitidas: contratos de transição, fontes de verdade e testes do map.
# W6-T03/F9.5 estreitou de diretórios amplos para arquivos específicos onde o
# literal legado é vocabulário congelado (schema const, edge label, mapa dual).
ALLOWED_PREFIXES = (
    # -- fontes de verdade do rename (ADR-093)
    "pipeline/stage_spec.py",  # STAGE_RENAME_MAP
    "pipeline/artifact_store.py",  # _STAGE_TO_SUFFIX + stage_aliases
    "pipeline/orchestrator.py",  # LEGACY_FROM_ALIASES
    # -- vocabulário congelado de payload/lineage (não é a coluna stage)
    "pipeline/domain/services/e3_reconciler_adapter.py",  # payload["pipeline_stage"] (schema)
    "pipeline/domain/services/e5_serialization.py",  # E5_OUTPUT_STAGE (label de edge)
    "pipeline/domain/services/lineage_fields.py",  # E5_STAGE (label de edge)
    "pipeline/domain/services/lineage_debug_tools.py",  # default de CLI de debug
    "backend/app/services/parecer_citation_lineage.py",  # src_stage="E5" (label de edge)
    # -- compat plumbing dual legacy+descritivo (janela F9.2 → F9.6)
    "backend/app/services/db_artifact_store.py",  # SCHEMA_BY_STAGE + _WORKSPACE_SCOPED_STAGES
    "backend/app/services/report_lineage.py",  # EXTRACTION_STAGES
    "backend/app/services/family_member_pii_service.py",  # query dual E1
    "backend/app/services/tributario_input_builder.py",  # tuplas duais E3/E4
    # -- migrations, ops e superfícies de teste
    "backend/alembic/versions/",  # migrations (STAGE_RENAME, imports, comentários)
    "backend/app/scripts/",  # backfill usa strings legadas
    "backend/scripts/",  # ops scripts varrem rows legados no DB
    "backend/tests/",  # testes de migration, DBArtifactStore, etc.
    "tests/",  # fixtures golden podem conter strings legadas
    "_scratch/",  # scripts de auditoria
    "config/",  # schemas JSON mencionam nomes de stage
    "docs/",  # ADRs históricos
)


SEARCH_ROOTS = ["pipeline", "scripts", "backend", "tests", "_scratch"]


def _iter_python_files():
    for root in SEARCH_ROOTS:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        for p in root_path.rglob("*.py"):
            if "__pycache__" in p.parts or ".venv" in p.parts:
                continue
            yield p


def _is_allowed(rel_path: str) -> bool:
    return any(rel_path.startswith(prefix) or rel_path == prefix for prefix in ALLOWED_PREFIXES)


@functools.lru_cache(maxsize=1)
def _find_occurrences() -> dict[str, tuple[tuple[str, int, str], ...]]:
    """Scan completo do repo, executado uma vez por sessão pytest.

    Sem o cache, parametrizar `test_legacy_name_only_in_allowed_files` por
    cada nome legado fazia o scan rodar N vezes (uma por param), com custo
    de ~1.5 s/scan × 19 nomes = ~28 s desperdiçados em pipeline-tests.
    Retorna tuplas (em vez de listas) para fechamento imutável compatível
    com `lru_cache`.
    """
    # Literal de string exato: "E5" / 'E5'. Prosa (comentário, docstring sem
    # aspas, log "E5: ...") não conta — só identificador em código vaza para
    # a coluna ``stage`` (W6-T03/F9.5).
    patterns = {name: re.compile(rf"""["']{re.escape(name)}["']""") for name in LEGACY_NAMES}
    out: dict[str, list[tuple[str, int, str]]] = {}
    for p in _iter_python_files():
        rel = p.relative_to(REPO_ROOT).as_posix()
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for name, pat in patterns.items():
            for i, line in enumerate(text.splitlines(), start=1):
                if pat.search(line):
                    out.setdefault(name, []).append((rel, i, line.strip()))
    return {name: tuple(items) for name, items in out.items()}


@pytest.mark.skipif(
    os.environ.get("MATHOMS_ENFORCE_STAGE_RENAME", "0") != "1",
    reason="Soft-fail mode default → teste não dá sinal de correctness em PR; rodar só "
    "quando MATHOMS_ENFORCE_STAGE_RENAME=1 (Fase 9.5+ vai inverter o default).",
)
@pytest.mark.parametrize("legacy_name", LEGACY_NAMES)
def test_legacy_name_only_in_allowed_files(legacy_name: str):
    """Hard-fail quando habilitado: vaza identificador legado → CI quebra."""
    occurrences = _find_occurrences().get(legacy_name, ())
    leaks = [(path, line, snippet) for path, line, snippet in occurrences if not _is_allowed(path)]
    if leaks:
        msg = (
            f"Identificador legado '{legacy_name}' vazou para {len(leaks)} localização(ões):\n"
            + "\n".join(f"  {p}:{l}: {s[:100]}" for p, l, s in leaks[:10])
        )
        pytest.fail(msg)
