"""Resolve o workspace (email OU uuid) → UUID + run alvo + inventário de artefatos E2/E3/E4.

Passo 1 da skill ledger-certify. Read-only sobre o DB configurado (``DATABASE_URL``);
funciona em SQLite local e Postgres. Rode da RAIZ do repo (carrega ``.env``):
``.venv/bin/python .claude/skills/ledger-certify/scripts/resolve_ledger.py <workspace> [--run <run_id>]``.

Saída: JSON em stdout com ``workspace_id``, ``run_id`` (alvo), e ``artifacts`` —
keys por stage (E2 extract_*, baseline, E3 reconcile, E4 categorize), lidas via
``stage_aliases`` (aceita legado + descritivo, ADR-093). Exit 1 se não resolver.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sqlalchemy import text

from backend.app.core.database import SyncSessionLocal
from pipeline.artifact_store import stage_aliases

_E2_STAGES = ("extract_statements", "extract_invoices", "extract_with_llm")
_STAGE_GROUPS = {
    "e2": _E2_STAGES,
    "baseline": ("consolidate_baseline",),
    "e3": ("reconcile_transactions",),
    "e4": ("categorize_transactions",),
}


def _resolve_id(db, workspace: str) -> str | None:
    if "@" in workspace:
        row = db.execute(
            text(
                "SELECT w.id FROM workspaces w JOIN users u ON u.id = w.owner_id "
                "WHERE u.email = :e ORDER BY w.created_at LIMIT 1"
            ),
            {"e": workspace},
        ).first()
        return row[0] if row else None
    exists = db.execute(text("SELECT id FROM workspaces WHERE id = :i"), {"i": workspace}).first()
    return exists[0] if exists else None


def _latest_run(db, ws: str) -> str | None:
    row = db.execute(
        text(
            "SELECT id FROM pipeline_runs WHERE workspace_id = :ws AND status = 'completed' "
            "ORDER BY started_at DESC LIMIT 1"
        ),
        {"ws": ws},
    ).first()
    return row[0] if row else None


def _keys_for(db, ws: str, stages: tuple[str, ...]) -> list[str]:
    aliases = sorted({a for s in stages for a in stage_aliases(s)})
    placeholders = ",".join(f":s{i}" for i in range(len(aliases)))
    params = {"ws": ws, **{f"s{i}": a for i, a in enumerate(aliases)}}
    rows = db.execute(
        text(
            f"SELECT DISTINCT artifact_key FROM pipeline_artifacts "
            f"WHERE workspace_id = :ws AND stage IN ({placeholders}) ORDER BY artifact_key"
        ),
        params,
    ).all()
    return [r[0] for r in rows]


def _inventory(db, ws: str) -> dict[str, list[str]]:
    return {group: _keys_for(db, ws, stages) for group, stages in _STAGE_GROUPS.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workspace", help="email ou uuid")
    parser.add_argument(
        "--run", default=None, help="run_id alvo (default: run completed mais recente)"
    )
    args = parser.parse_args()
    with SyncSessionLocal() as db:
        ws = _resolve_id(db, args.workspace)
        if ws is None:
            print(json.dumps({"error": f"workspace não encontrado: {args.workspace!r}"}))
            return 1
        run_id = args.run or _latest_run(db, ws)
        out = {"workspace_id": ws, "run_id": run_id, "artifacts": _inventory(db, ws)}
    print(json.dumps(out, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
