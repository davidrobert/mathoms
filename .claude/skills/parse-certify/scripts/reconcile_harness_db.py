"""Cross-check harness↔DB do Passo 3 do parse-certify — a cola de leitura do DB.

Alimenta os 2 inputs de ``dev.harness_db_reconcile.reconcile`` a partir do DB real:

- ``db_hashes``: ``SELECT content_hash FROM documents WHERE workspace_id`` (set).
- ``live_artifacts``: pares ``(stage, key)`` **vivos NÃO-fallback** — mais recente
  por ``(stage canônico, key)`` (replica o read-path workspace-latest), payload
  não-stub. Stub = ``requires_llm_fallback`` True OU ``transacoes == []`` (bank
  statement parseado com zero tx; artefato de investimento **não** tem a chave
  ``transacoes`` → ``.get`` devolve None, logo não é stub).

Os ``harness_records`` vêm de um snapshot do ``dev/certify_parse_local.py``
(``--baseline``, que já emite ``content_hash`` por doc) **ou** são gerados inline
com ``--dir``. Read-only. Rode da RAIZ do repo (carrega ``.env``):

    .venv/bin/python .claude/skills/parse-certify/scripts/reconcile_harness_db.py \\
        <workspace> --records <harness_baseline.json>
    .venv/bin/python .claude/skills/parse-certify/scripts/reconcile_harness_db.py \\
        <workspace> --dir <storage/<uuid>/data/financial_statements>

Exit 1 se ``not_ingested`` (P0) ou violação de invariante; 0 se limpo.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from resolve_workspace_dirs import _resolve_id
from sqlalchemy import select, text

from backend.app.core.database import SyncSessionLocal
from backend.app.models.pipeline_artifact import PipelineArtifact
from dev.harness_db_reconcile import ReconResult, is_stub, reconcile
from pipeline.artifact_store import stage_aliases
from pipeline.stage_spec import resolve_stage_name

# Stages E2/E3/E4 relevantes (descritivos; ``stage_aliases`` pega o legado).
_STAGES = (
    "extract_statements",
    "extract_invoices",
    "extract_with_llm",
    "reconcile_transactions",
    "categorize_transactions",
)


def _decrypt(payload: dict) -> dict:
    from backend.app.services.security.crypto import (
        decrypt_artifact_payload,
        is_encrypted_payload,
    )

    return decrypt_artifact_payload(payload) if is_encrypted_payload(payload) else payload


def _artifact_rows(session, ws: str) -> list:
    aliases = sorted({a for s in _STAGES for a in stage_aliases(s)})
    stmt = select(PipelineArtifact).where(
        PipelineArtifact.workspace_id == ws,
        PipelineArtifact.stage.in_(aliases),
    )
    return list(session.execute(stmt).scalars())


def _latest_by_canonical(rows: list) -> dict:
    """Mais recente por ``(stage canônico, key)`` (``created_at`` desc, ``id`` desc)
    — replica ``DBArtifactStore._get_latest_in_workspace``; ≤1 por chave, logo o
    invariante nunca dispara falso (o dado real tem ~30 rows/chave entre runs)."""
    best: dict = {}
    for row in rows:
        unit = (resolve_stage_name(row.stage), row.artifact_key)
        incumbent = best.get(unit)
        if incumbent is None or (row.created_at, row.id) > (incumbent.created_at, incumbent.id):
            best[unit] = row
    return best


def _live_artifacts(session, ws: str) -> list[tuple[str, str]]:
    """``(stage, key)`` vivos não-fallback (mais recente por chave, não-stub)."""
    out = []
    for (stage, key), row in _latest_by_canonical(_artifact_rows(session, ws)).items():
        if not is_stub(_decrypt(row.content_json)):
            out.append((stage, key))
    return out


def _db_hashes(session, ws: str) -> set[str]:
    rows = session.execute(
        text("SELECT content_hash FROM documents WHERE workspace_id=:w"), {"w": ws}
    ).all()
    return {r[0] for r in rows if r[0]}


def _records_from_dir(dir_path: Path) -> list[dict]:
    from dev.certify_parse_local import _init_pipeline_config, run_dir

    _init_pipeline_config()  # sem isso o parse Wise degrada p/ 0 tx (root errado)
    return run_dir(dir_path)


def _load_records(args: argparse.Namespace) -> list[dict]:
    if args.dir is not None:
        return _records_from_dir(args.dir)
    return json.loads(args.records.read_text(encoding="utf-8"))


def _format(ws: str, r: ReconResult) -> str:
    lines = [
        f"# parse-certify reconcile — ws {ws[:8]}",
        f"ingested: {r.ingested} · deduped (benigno, DB ≤ dir): {r.deduped}",
        f"not_ingested (P0 — parseado mas ausente no DB): {len(r.not_ingested)}",
    ]
    lines += [f"  · {lbl}" for lbl in r.not_ingested]
    lines.append(f"invariante ≤1 vivo não-fallback: {len(r.invariant_violations)} violação(ões)")
    lines += [f"  · {v}" for v in r.invariant_violations]
    lines.append(f"clean: {r.clean}")
    return "\n".join(lines)


def _silence_sql_echo() -> None:
    for name in ("sqlalchemy.engine", "sqlalchemy.engine.Engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _reconcile_workspace(session, args: argparse.Namespace):
    ws = _resolve_id(session, args.workspace)
    if ws is None:
        return None
    records = _load_records(args)
    db_hashes = _db_hashes(session, ws)
    result = reconcile(
        records,
        db_hashes,
        _live_artifacts(session, ws),
        db_prefixes={h[:12] for h in db_hashes},
    )
    return ws, result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workspace", help="email ou uuid")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--records", type=Path, help="snapshot do certify_parse_local.py (--baseline)")
    src.add_argument("--dir", type=Path, help="roda o harness inline sobre a pasta de documentos")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    _silence_sql_echo()
    with SyncSessionLocal() as session:
        outcome = _reconcile_workspace(session, args)
    if outcome is None:
        print(json.dumps({"error": f"workspace não encontrado: {args.workspace!r}"}))
        return 1
    ws, result = outcome
    print(_format(ws, result))
    return 0 if result.clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
