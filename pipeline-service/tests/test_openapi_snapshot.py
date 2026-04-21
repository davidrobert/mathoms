"""Snapshot — ``docs/api/v1/pipeline-service.openapi.json`` stays in sync.

Same contract as `backend/tests/test_openapi_snapshot.py`: changing the
pipeline-service spec must land together with a snapshot refresh
(``make update-pipeline-service-openapi``).
"""

from __future__ import annotations

import json
from pathlib import Path


_SERVICE_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVICE_ROOT.parent
_SNAPSHOT_PATH = _REPO_ROOT / "docs" / "api" / "v1" / "pipeline-service.openapi.json"


def test_openapi_snapshot_matches_committed_file() -> None:
    from app.main import create_app

    assert _SNAPSHOT_PATH.exists(), (
        f"Snapshot ausente em {_SNAPSHOT_PATH}. Rode "
        "``make update-pipeline-service-openapi`` para gerá-lo."
    )

    current = create_app().openapi()
    current_text = json.dumps(current, indent=2, sort_keys=True) + "\n"
    committed = _SNAPSHOT_PATH.read_text(encoding="utf-8")

    if current_text != committed:
        import difflib
        diff = "".join(
            difflib.unified_diff(
                committed.splitlines(keepends=True),
                current_text.splitlines(keepends=True),
                fromfile="docs/api/v1/pipeline-service.openapi.json",
                tofile="create_app().openapi() (current)",
                n=3,
            )
        )
        raise AssertionError(
            "pipeline-service OpenAPI snapshot desatualizado. Rode "
            "``make update-pipeline-service-openapi`` e comite o diff.\n\n"
            + (diff[:8000] + "\n... [diff truncado]" if len(diff) > 8000 else diff)
        )
