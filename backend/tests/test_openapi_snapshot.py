"""Snapshot test — ``docs/api/v1/openapi.json`` bate com o spec atual.

A6f.2 (ADR-102 · R18): o snapshot é o contrato canônico. Qualquer mudança
não-intencional no OpenAPI (novo campo, remoção de campo, tipo alterado)
deve ser capturada aqui antes de ir para produção.

Se este teste falha, rode ``make update-openapi-snapshot`` (ou regenere
manualmente — ver `docs/api/v1/README.md`) e comite o diff.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.main import app


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SNAPSHOT_PATH = _REPO_ROOT / "docs" / "api" / "v1" / "openapi.json"


def test_openapi_snapshot_matches_committed_file() -> None:
    """Gera o spec em memória e compara com o snapshot em disco.

    Usa ``sort_keys=True`` e ``indent=2`` (os mesmos do gerador) para que
    o diff seja determinístico.
    """
    assert _SNAPSHOT_PATH.exists(), (
        f"Snapshot ausente em {_SNAPSHOT_PATH}. Rode "
        "``make update-openapi-snapshot`` para gerá-lo."
    )

    current = app.openapi()
    current_text = json.dumps(current, indent=2, sort_keys=True) + "\n"
    committed_text = _SNAPSHOT_PATH.read_text(encoding="utf-8")

    if current_text != committed_text:
        # Diff útil em caso de falha — pytest truncaria strings longas.
        import difflib

        diff = "".join(
            difflib.unified_diff(
                committed_text.splitlines(keepends=True),
                current_text.splitlines(keepends=True),
                fromfile="docs/api/v1/openapi.json",
                tofile="app.openapi() (current)",
                n=3,
            )
        )
        raise AssertionError(
            "OpenAPI snapshot desatualizado. Rode "
            "``make update-openapi-snapshot`` e comite o diff.\n\n"
            + (diff[:8000] + "\n... [diff truncado]" if len(diff) > 8000 else diff)
        )
