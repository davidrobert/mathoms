"""Snapshot test dos índices materializados em docs/_MOC/_generated/ (ADR-182, F1)."""
# Padrão de tests/test_openapi_snapshot.py / tests/test_snapshot_changelog.py:
# o que está em disco deve bater byte-a-byte com o regenerado por
# dev/build_doc_index.py — drift em _generated/ falha o teste com mensagem
# que aponta o comando para corrigir.

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_DIR = REPO_ROOT / "dev"
DOCS = REPO_ROOT / "docs"
GENERATED = DOCS / "_MOC" / "_generated"

# Adiciona dev/ ao path antes do import (sem editar conftest global).
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))


@pytest.fixture(scope="module")
def regenerated() -> dict[str, str]:
    """Roda build_doc_index.regenerate_all sobre a vault e retorna {filename: content}."""
    import build_doc_index  # noqa: PLC0415

    return build_doc_index.regenerate_all(DOCS)


@pytest.mark.parametrize(
    "filename",
    [
        "INDEX.md",
        "ADR_INDEX.md",
        "SPRINT_CURRENT.md",
        "CHANGELOG_RECENT.md",
        "ROADMAP.md",
        "PLAN_PROGRESS.md",
        "DOC_STATS.md",
        "CONTEXT_INDEX.md",
        "CONTEXT_ENGINEERING.md",
        "CONTEXT_BACKEND.md",
        "CONTEXT_FRONTEND.md",
        "CONTEXT_PRODUCT.md",
        "CONTEXT_DOCS.md",
    ],
)
def test_generated_file_matches_source(regenerated: dict[str, str], filename: str) -> None:
    target = GENERATED / filename
    assert target.is_file(), (
        f"{target.relative_to(REPO_ROOT)} ausente. "
        "Rode `python3 dev/build_doc_index.py --inline`."
    )
    expected = regenerated[filename]
    actual = target.read_text(encoding="utf-8")
    assert actual == expected, (
        f"{target.relative_to(REPO_ROOT)} fora de sync com a vault. "
        "Rode `python3 dev/build_doc_index.py --inline` e comite o diff."
    )
