"""Snapshot test — ``docs/DB_SCHEMA_REFERENCE.md`` bate com o schema atual.

A6f.4 (ADR-102 · R20): o doc de referência é gerado por
``dev/generate_db_schema_reference.py`` introspeccionando ``Base.metadata``.
Qualquer mudança no schema (nova tabela, coluna, constraint, index, mudança
de tipo) deve ser refletida no doc committed.

Se este teste falha, rode ``make update-db-schema-reference`` e comite o
diff gerado.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(_REPO_ROOT))

from dev.generate_db_schema_reference import SNAPSHOT_PATH, generate  # noqa: E402


def test_db_schema_reference_snapshot_matches_metadata() -> None:
    """Compara o markdown committed com o output atual do gerador.

    Usa comparação exata de bytes — o gerador é determinístico
    (verificado em A6f.4).
    """
    assert SNAPSHOT_PATH.exists(), (
        f"Snapshot ausente em {SNAPSHOT_PATH}. Rode "
        "``make update-db-schema-reference`` para gerá-lo."
    )

    current = generate()
    committed = SNAPSHOT_PATH.read_text(encoding="utf-8")

    if current != committed:
        import difflib

        diff = "".join(
            difflib.unified_diff(
                committed.splitlines(keepends=True),
                current.splitlines(keepends=True),
                fromfile="docs/DB_SCHEMA_REFERENCE.md (committed)",
                tofile="generate() (current)",
                n=3,
            )
        )
        raise AssertionError(
            "DB_SCHEMA_REFERENCE.md desatualizado. Rode "
            "``make update-db-schema-reference`` e comite o diff.\n\n"
            + (diff[:8000] + "\n... [diff truncado]" if len(diff) > 8000 else diff)
        )
