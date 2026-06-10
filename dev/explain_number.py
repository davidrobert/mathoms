#!/usr/bin/env python3
"""Explica um número do relatório via lineage field-level (ADR-279/ADR-281 · A24.l5).

Casca fina: roda a fixture sintética dogfood in-memory
(``tests.pipeline_golden_substrate.run_dogfood_pipeline``), resolve a árvore
com ``LineageResolver`` e imprime o render de
``pipeline/domain/services/lineage_render.py`` — sem abrir arquivo de stage.
Uso: ``python3 dev/explain_number.py --field patrimonio.liquido``.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

_DOGFOOD = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"


def _run_dogfood() -> dict:
    from tests.pipeline_golden_substrate import (
        load_fixture,
        run_dogfood_pipeline,
        write_e5_config,
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_e5_config(root)
        with contextlib.redirect_stdout(io.StringIO()):
            return run_dogfood_pipeline(
                root,
                raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
                e2_extracts={
                    "fict_a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
                    "fict_b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
                },
            )


def _resolve(payload: dict, field: str) -> dict:
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.domain.services.lineage_resolver import LineageResolver

    store = InMemoryArtifactStore()
    store.seed("E5", "analise_financeira", payload)
    return LineageResolver(store).resolve("E5", "analise_financeira", field)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--field", default="patrimonio.liquido", help="dot-path no payload E5")
    args = parser.parse_args(argv)

    from pipeline.domain.services.lineage_render import render_lineage_tree

    node = _resolve(_run_dogfood(), args.field)
    print(render_lineage_tree(node))
    return 1 if node["node_type"] == "dangling" else 0


if __name__ == "__main__":
    raise SystemExit(main())
