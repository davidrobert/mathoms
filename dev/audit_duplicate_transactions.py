#!/usr/bin/env python3
"""Audita workspaces afetados pelo bug de tx duplicadas cross-document (ADR-255)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _decrypt_payload(content_json):
    """Reusa lógica do DBArtifactStore para Fernet decrypt."""
    from backend.app.services.storage.db_artifact_store import _maybe_decrypt

    payload = json.loads(content_json) if isinstance(content_json, str) else content_json
    return _maybe_decrypt(payload)


def _ingest_row(index: dict, row) -> None:
    """Lê 1 row E3 e popula o índice (best-effort em decrypt fail)."""
    workspace_id, run_id, artifact_key, content_json = row
    try:
        data = _decrypt_payload(content_json)
    except Exception as exc:  # noqa: BLE001 — best-effort audit
        print(f"  ! skip {artifact_key} (decrypt fail: {exc})", file=sys.stderr)
        return
    for tx in data.get("transacoes") or []:
        key = _forensic_key(tx)
        if key is not None:
            index[workspace_id][run_id][key].append(artifact_key)


def _index_transactions(rows) -> dict:
    """Constrói índice workspace → run → (hash_forense) → list[artifact_key]."""
    index: dict[str, dict[str, dict[tuple, list[str]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for row in rows:
        _ingest_row(index, row)
    return index


def _forensic_key(tx: dict) -> tuple | None:
    data = tx.get("data") or ""
    valor = tx.get("valor")
    desc = (tx.get("descricao") or "").strip().lower()
    if not data or valor is None or not desc:
        return None
    try:
        cents = int(round(float(valor) * 100))
    except (TypeError, ValueError):
        return None
    return (data, cents, desc)


def _run_entry(workspace_id: str, run_id: str, dup_hashes: dict) -> dict:
    """Formata entrada de relatório por (workspace, run)."""
    sample = sorted(dup_hashes.items(), key=lambda x: -len(x[1]))[:3]
    return {
        "workspace_id": workspace_id,
        "pipeline_run_id": run_id,
        "dup_unique_txs": len(dup_hashes),
        "total_extra_copies": sum(len(keys) - 1 for keys in dup_hashes.values()),
        "sample": [
            {"data": h[0], "cents": h[1], "descricao_lower": h[2][:60], "keys": keys[:5]}
            for h, keys in sample
        ],
    }


def _iter_workspace_runs(index: dict):
    """Yield (workspace_id, run_id, hash_map) em ordem estável."""
    for workspace_id, runs in sorted(index.items()):
        for run_id, hash_map in sorted(runs.items()):
            yield workspace_id, run_id, hash_map


def _summarize(index: dict) -> list[dict]:
    """Filtra hashes com >1 key e formata entradas afetadas."""
    affected: list[dict] = []
    for workspace_id, run_id, hash_map in _iter_workspace_runs(index):
        dups = {h: keys for h, keys in hash_map.items() if len(keys) > 1}
        if dups:
            affected.append(_run_entry(workspace_id, run_id, dups))
    return affected


def _connect(db_url: str):
    from sqlalchemy import create_engine

    # SQLAlchemy não aceita sqlite+aiosqlite p/ sync engine — sanitize.
    if db_url.startswith("sqlite+aiosqlite:"):
        db_url = db_url.replace("sqlite+aiosqlite:", "sqlite:", 1)
    return create_engine(db_url)


def _fetch_e3_rows(db_url: str):
    from sqlalchemy import text

    engine = _connect(db_url)
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT workspace_id, pipeline_run_id, artifact_key, content_json "
                "FROM pipeline_artifacts WHERE stage IN ('E3', 'reconcile_transactions')"
            )
        ).all()


def _emit(output_path: str, payload: str) -> None:
    if output_path == "-":
        print(payload)
        return
    Path(output_path).write_text(payload, encoding="utf-8")
    print(f"[audit] gravado em {output_path}", file=sys.stderr)


def _parse_argv(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", default=os.environ.get("MATHOMS_DATABASE_URL", ""))
    parser.add_argument("--output", default="-")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_argv(argv)
    if not args.db_url:
        print("error: --db-url ou MATHOMS_DATABASE_URL obrigatório", file=sys.stderr)
        return 2
    rows = _fetch_e3_rows(args.db_url)
    print(f"[audit] {len(rows)} E3 artifacts varridos", file=sys.stderr)
    affected = _summarize(_index_transactions(rows))
    print(f"[audit] {len(affected)} workspaces×runs afetados", file=sys.stderr)
    _emit(
        args.output,
        json.dumps(
            {"affected_count": len(affected), "affected": affected},
            indent=2,
            ensure_ascii=False,
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
