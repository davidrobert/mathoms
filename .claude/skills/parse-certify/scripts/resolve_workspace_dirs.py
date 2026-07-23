"""Resolve o workspace (email OU uuid) → dirs de storage no disco + inventário do DB.

Passo 1 da skill parse-certify. Mapeia ``email|uuid`` para as pastas de documentos
em ``storage/<uuid>/data/<grupo>/`` (onde o harness ``dev/certify_parse_local.py``
aponta o ``--dir``) e traz o inventário do DB para o cross-check (contagem por
doc_type, needs_review, possíveis duplicatas). Roda contra ``DATABASE_URL``
(SQLite local ou Postgres). Rode da RAIZ do repo (carrega ``.env``):
``.venv/bin/python .claude/skills/parse-certify/scripts/resolve_workspace_dirs.py <workspace>``.

Saída: JSON em stdout com ``workspace_id``, ``groups`` (grupo, dir absoluto,
n_files por sufixo aceito), ``db`` (docs, needs_review, possible_duplicate,
doc_type_hist). Exit 1 se não resolver. Espelha o ``resolve_workspace.py`` do
pipeline-review (email→uuid duplicado; extrair na 3ª skill).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal

VALID_SUFFIXES = {".pdf", ".csv", ".xls", ".xlsx"}

# Grupos de data/ certificáveis pelo harness E0→E2. financial_statements é o
# único no escopo v1 — os demais passam por outros stages (extract_baseline,
# extract_comprovantes_bens) e sairiam como falso 'não-coberto' no harness E2.
DATA_GROUPS = (
    "financial_statements",
    "income_tax_br",
    "income_tax_us",
    "real_estate",
    "vehicles",
)
V1_SCOPE = "financial_statements"


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


def _count_files(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for f in directory.iterdir() if f.is_file() and f.suffix.lower() in VALID_SUFFIXES)


def _groups(workspace_id: str) -> list[dict]:
    root = Path(settings.STORAGE_ROOT).resolve() / workspace_id / "data"
    out = []
    for group in DATA_GROUPS:
        directory = root / group
        out.append(
            {
                "group": group,
                "dir": str(directory),
                "n_files": _count_files(directory),
                "in_scope_v1": group == V1_SCOPE,
            }
        )
    return out


def _db_inventory(db, ws: str) -> dict:
    docs = db.execute(
        text("SELECT COUNT(*) FROM documents WHERE workspace_id = :ws"), {"ws": ws}
    ).scalar()
    needs_review = db.execute(
        text("SELECT COUNT(*) FROM documents WHERE workspace_id = :ws AND needs_review = 1"),
        {"ws": ws},
    ).scalar()
    possible_dup = db.execute(
        text(
            "SELECT COUNT(*) FROM documents WHERE workspace_id = :ws "
            "AND possible_duplicate_of_id IS NOT NULL"
        ),
        {"ws": ws},
    ).scalar()
    hist = db.execute(
        text(
            "SELECT doc_type, COUNT(*) FROM documents WHERE workspace_id = :ws "
            "GROUP BY doc_type ORDER BY COUNT(*) DESC"
        ),
        {"ws": ws},
    ).all()
    return {
        "docs": docs,
        "needs_review": needs_review,
        "possible_duplicate": possible_dup,
        "doc_type_hist": {str(dt): n for dt, n in hist},
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: resolve_workspace_dirs.py <email|uuid>", file=sys.stderr)
        return 2
    with SyncSessionLocal() as db:
        ws = _resolve_id(db, sys.argv[1])
        if ws is None:
            print(json.dumps({"error": f"workspace não encontrado: {sys.argv[1]!r}"}))
            return 1
        out = {"workspace_id": ws, "groups": _groups(ws), "db": _db_inventory(db, ws)}
    print(json.dumps(out, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
