"""Resolve o workspace (email OU uuid) → UUID + baseline + guarda de run ativo.

Passo 1 da skill pipeline-review. Roda contra o DB configurado (``DATABASE_URL``),
então funciona em SQLite local e Postgres. Rode a partir da RAIZ do repo (carrega
``.env``): ``.venv/bin/python .claude/skills/pipeline-review/scripts/resolve_workspace.py <workspace>``.

Saída: JSON em stdout com ``workspace_id``, ``latest_report``, ``latest_run``,
``active_run`` (bloqueante), ``docs``, ``needs_review``. Exit 1 se não resolver.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sqlalchemy import text

from backend.app.core.database import SyncSessionLocal


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


def _one(db, sql: str, ws: str) -> dict | None:
    row = db.execute(text(sql), {"ws": ws}).mappings().first()
    return dict(row) if row else None


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: resolve_workspace.py <email|uuid>", file=sys.stderr)
        return 2
    with SyncSessionLocal() as db:
        ws = _resolve_id(db, sys.argv[1])
        if ws is None:
            print(json.dumps({"error": f"workspace não encontrado: {sys.argv[1]!r}"}))
            return 1
        out = {
            "workspace_id": ws,
            "latest_report": _one(
                db,
                "SELECT id, title, period, created_at, pipeline_run_id FROM reports "
                "WHERE workspace_id = :ws ORDER BY created_at DESC LIMIT 1",
                ws,
            ),
            "latest_run": _one(
                db,
                "SELECT id, status, tier_at_run, started_at, completed_at FROM pipeline_runs "
                "WHERE workspace_id = :ws ORDER BY started_at DESC LIMIT 1",
                ws,
            ),
            "active_run": _one(
                db,
                "SELECT id, status FROM pipeline_runs WHERE workspace_id = :ws "
                "AND status IN ('running','pending','paused') LIMIT 1",
                ws,
            ),
            "docs": (
                db.execute(
                    text("SELECT COUNT(*) FROM documents WHERE workspace_id = :ws"), {"ws": ws}
                ).scalar()
            ),
            "needs_review": (
                db.execute(
                    text(
                        "SELECT COUNT(*) FROM documents WHERE workspace_id = :ws AND needs_review = 1"
                    ),
                    {"ws": ws},
                ).scalar()
            ),
        }
    print(json.dumps(out, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
