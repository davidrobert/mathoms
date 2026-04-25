"""Garantia de paridade entre `STAGE_RENAME_MAP` (backend) e
`pipelineStageNames.ts` (frontend).

Bug histórico (2026-04-25, F9.2): emissores de `stage_activity` em
`pipeline/stages/*.py` e `scripts/e2_extract.py` ainda passam keys
legadas (`E2-extratos`, `E1.5`…), mas `stage_logs[].stage` na UI já
chega em formato descritivo (`extract_statements`, `extract_baseline`…).
Sem o mapping correto no frontend, o filtro
`liveStageActivity?.stage === stage.stage` retornava false e o painel
`LiveStepProgress` (arquivo atual, item N de M, fase) sumia.

Este teste falha se alguém adicionar/remover stage no
`STAGE_RENAME_MAP` sem espelhar em `frontend/src/lib/pipelineStageNames.ts`.
"""

from __future__ import annotations

import re
from pathlib import Path

from pipeline.stage_spec import STAGE_RENAME_MAP

REPO_ROOT = Path(__file__).resolve().parents[1]
TS_PATH = REPO_ROOT / "frontend/src/lib/pipelineStageNames.ts"


def _parse_ts_legacy_to_descriptive() -> dict[str, str]:
    src = TS_PATH.read_text(encoding="utf-8")
    body_match = re.search(
        r"LEGACY_TO_DESCRIPTIVE\s*:\s*Record<[^>]+>\s*=\s*\{([^}]*)\}",
        src,
        re.DOTALL,
    )
    assert body_match, "não achei `LEGACY_TO_DESCRIPTIVE` em pipelineStageNames.ts"
    body = body_match.group(1)
    pairs = re.findall(r'"([\w.\-]+)":\s*"([\w.\-]+)"', body)
    return dict(pairs)


def test_frontend_legacy_to_descriptive_matches_backend() -> None:
    parsed = _parse_ts_legacy_to_descriptive()
    assert parsed == STAGE_RENAME_MAP, (
        "Mapping desincronizou. Atualize `frontend/src/lib/pipelineStageNames.ts` "
        "para refletir `pipeline.stage_spec.STAGE_RENAME_MAP`. "
        f"\nbackend (verdade): {STAGE_RENAME_MAP}"
        f"\nfrontend (atual): {parsed}"
    )
