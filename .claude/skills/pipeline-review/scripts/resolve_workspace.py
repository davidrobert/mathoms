"""Resolve o workspace (email OU uuid) → UUID + baseline + guarda de run ativo.

Passo 1 da skill pipeline-review. Roda contra o DB configurado (``DATABASE_URL``),
então funciona em SQLite local e Postgres. Rode a partir da RAIZ do repo (carrega
``.env``): ``.venv/bin/python .claude/skills/pipeline-review/scripts/resolve_workspace.py <workspace>``.

Saída: JSON em stdout com ``workspace_id``, ``latest_report``, ``latest_run``,
``active_run`` (bloqueante), ``docs``, ``documents_needs_review`` e
``pending_stage_reviews`` (resolva-as por ``resolve_pause.py``). Exit 1 se não resolver.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sqlalchemy import text

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_run import PipelineRunStatus

# Terminal e a lista curta e estavel; "em voo" e o COMPLEMENTO, para status novo
# no enum entrar como bloqueante por default em vez de sumir do guard. A versao
# anterior filtrava `paused` (que nunca existiu em PipelineRunStatus) e omitia
# `needs_review` e `resuming`: um run pausado aguardando revisao era reportado
# como `active_run: null` e a skill autorizava disparar run por cima.
TERMINAL = {
    PipelineRunStatus.completed,
    PipelineRunStatus.partial_failure,
    PipelineRunStatus.failed,
    PipelineRunStatus.cancelled,
}
EM_VOO = tuple(s.value for s in PipelineRunStatus if s not in TERMINAL)


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


def _pendentes(db, ws: str) -> list[dict]:
    """Conferências sem decisão do run pausado — o que `resolve_pause.py` vai resolver."""
    rows = db.execute(
        text(
            "SELECT sr.id AS review_id, sr.stage FROM stage_reviews sr "
            "JOIN pipeline_runs r ON r.id = sr.pipeline_run_id "
            "WHERE r.workspace_id = :ws AND r.status = 'needs_review' "
            "AND sr.status NOT IN ('approved', 'edited')"
        ),
        {"ws": ws},
    ).mappings()
    return [dict(r) for r in rows]


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
                "SELECT id, status, paused_at_stage FROM pipeline_runs WHERE workspace_id = :ws "
                f"AND status IN ({','.join(repr(s) for s in EM_VOO)}) "
                "ORDER BY started_at DESC LIMIT 1",
                ws,
            ),
            "docs": (
                db.execute(
                    text("SELECT COUNT(*) FROM documents WHERE workspace_id = :ws"), {"ws": ws}
                ).scalar()
            ),
            # Renomeada: a chave dizia `needs_review` e contava DOCUMENTOS, homônima do
            # status do RUN logo acima. Quem lia o JSON via `needs_review: 0` e concluía
            # que não havia pausa.
            "documents_needs_review": (
                db.execute(
                    text(
                        "SELECT COUNT(*) FROM documents WHERE workspace_id = :ws AND needs_review = 1"
                    ),
                    {"ws": ws},
                ).scalar()
            ),
            "pending_stage_reviews": _pendentes(db, ws),
        }
    print(json.dumps(out, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
