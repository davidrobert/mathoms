"""Validação de paridade: adapter vs arquivo legado (ADR-077).

Compara o goals.json gerado pelo adapter com o arquivo original para
garantir que o cutover não produz regressão.

Uso:
    python -m backend.app.scripts.validate_adapter_parity --workspace-id <uuid>
    python -m backend.app.scripts.validate_adapter_parity  # busca por family_surname

Saída:
- Para cada seção do goals.json, compara valor do adapter vs arquivo.
- Diferenças em `_source`, `_adapter_version`, `_comment`, timestamps
  são toleradas (expected metadata).
- Diferenças em dados financeiros (if_meta, trs_pct, etc.) = FAIL.

Exit code 0 = paridade OK, 1 = diff encontrado, 2 = erro de setup.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.workspace import Workspace
from backend.app.services.pipeline_adapter import build_goals_payload

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GOALS_JSON_PATH = REPO_ROOT / "config" / "goals.json"
FAMILY_SURNAME_MATCH = "Ferreira Campos"

# Chaves que são esperadamente diferentes entre adapter e arquivo
TOLERATED_KEYS: set[str] = {
    "_source",
    "_adapter_version",
    "_comment",
    "_ultima_atualizacao",
    "_fonte",
    "_nota_taxa_retirada",
}

logger = logging.getLogger("validate_parity")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _deep_compare(
    path: str,
    original: Any,
    adapted: Any,
    diffs: list[str],
) -> None:
    """Compara recursivamente, ignora chaves em TOLERATED_KEYS."""
    if isinstance(original, dict) and isinstance(adapted, dict):
        all_keys = set(original) | set(adapted)
        for k in sorted(all_keys):
            if k in TOLERATED_KEYS:
                continue
            if k not in original:
                # Chave nova no adapter — pode ser enriquecimento do DB
                continue
            if k not in adapted:
                diffs.append(f"MISSING in adapter: {path}.{k}")
                continue
            _deep_compare(f"{path}.{k}", original[k], adapted[k], diffs)
    elif isinstance(original, list) and isinstance(adapted, list):
        if len(original) != len(adapted):
            diffs.append(
                f"LIST LENGTH DIFF: {path} — original={len(original)}, adapter={len(adapted)}"
            )
            return
        for i, (o, a) in enumerate(zip(original, adapted)):
            _deep_compare(f"{path}[{i}]", o, a, diffs)
    elif isinstance(original, (int, float)) and isinstance(adapted, (int, float)):
        if abs(original - adapted) > 0.01:
            diffs.append(f"VALUE DIFF: {path} — original={original}, adapter={adapted}")
    elif original != adapted:
        diffs.append(f"VALUE DIFF: {path} — original={repr(original)}, adapter={repr(adapted)}")


async def validate(workspace_id: str | None) -> int:
    if not GOALS_JSON_PATH.exists():
        logger.error("goals.json não encontrado: %s", GOALS_JSON_PATH)
        return 2

    original = json.loads(GOALS_JSON_PATH.read_text(encoding="utf-8"))
    logger.info(
        "Loaded original goals.json (%d top-level keys)",
        len(original),
    )

    async with AsyncSessionLocal() as db:
        if workspace_id:
            stmt = select(Workspace).where(Workspace.id == workspace_id)
        else:
            stmt = select(Workspace).where(Workspace.family_surname == FAMILY_SURNAME_MATCH)
        ws = (await db.execute(stmt)).scalar_one_or_none()
        if not ws:
            logger.error("Workspace não encontrada")
            return 2

        adapted = await build_goals_payload(ws.id, db=db)

    logger.info(
        "Adapter payload (%d top-level keys, _adapter_version=%s)",
        len(adapted),
        adapted.get("_adapter_version"),
    )

    diffs: list[str] = []
    # Compara seção por seção — adapter deve conter tudo do original
    for key in original:
        if key in TOLERATED_KEYS:
            continue
        if key not in adapted:
            diffs.append(f"SECTION MISSING in adapter: {key}")
            continue
        _deep_compare(key, original[key], adapted[key], diffs)

    if not diffs:
        logger.info("✓ PARIDADE OK — zero diferenças significativas.")
        return 0

    logger.error("✗ %d diferença(s) encontrada(s):", len(diffs))
    for d in diffs:
        logger.error("  - %s", d)
    logger.error(
        "\nPré-requisito de cutover não atendido. "
        "Corrija o adapter ou o seed antes de remover goals.json."
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", default=None)
    args = parser.parse_args()
    return asyncio.run(validate(args.workspace_id))


if __name__ == "__main__":
    sys.exit(main())
