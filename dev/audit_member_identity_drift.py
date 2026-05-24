#!/usr/bin/env python3
"""Audita drift de membro identity (CPF → >1 member_key) por workspace (ADR-267)."""

# Itera pipeline_artifacts stage='E4' artifact_key='patrimonio' (e E1.5c
# baseline_patrimonial), agrupa items por (workspace, cpf_normalizado),
# reporta workspaces com >1 member_key apontando para o mesmo CPF — sinal
# de R$ inflado por slug-de-nome variante (Mariana solteira vs casada).
# Critério #1 do fix ADR-267: zero workspaces affected após backfill.

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Carrega .env para MATHOMS_FERNET_KEY (necessário pra decrypt do payload).
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass  # python-dotenv não instalado — caller deve setar env manualmente.


def _decrypt_payload(content_json):
    """Reusa lógica do DBArtifactStore para Fernet decrypt."""
    from backend.app.services.db_artifact_store import _maybe_decrypt

    payload = json.loads(content_json) if isinstance(content_json, str) else content_json
    return _maybe_decrypt(payload)


def _normalize_cpf(value) -> str:
    """ADR-267 D3: strip não-dígitos, exige 11 chars."""
    if not value:
        return ""
    digits = "".join(c for c in str(value) if c.isdigit())
    return digits if len(digits) == 11 else ""


def _ingest_row(index: dict, row) -> None:
    """Lê 1 row patrimônio e popula índice (workspace → cpf → set[member_key])."""
    workspace_id, run_id, artifact_key, content_json = row
    try:
        data = _decrypt_payload(content_json)
    except Exception as exc:  # noqa: BLE001 — best-effort audit
        print(f"  ! skip {artifact_key} (decrypt fail: {exc})", file=sys.stderr)
        return
    for item in data.get("itens") or []:
        membro = item.get("membro") or ""
        cpf = _normalize_cpf(item.get("cpf"))
        if membro and cpf:
            index[workspace_id][cpf].add(membro)


def _index_members(rows) -> dict:
    """Constrói índice workspace → cpf → set[member_key]."""
    index: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        _ingest_row(index, row)
    return index


def _run_entry(workspace_id: str, cpf_collisions: dict) -> dict:
    """Formata entrada de relatório por workspace."""
    return {
        "workspace_id": workspace_id,
        "cpf_collision_count": len(cpf_collisions),
        "samples": [
            {
                "cpf_last4": cpf[-4:] if cpf else "?",  # last4 para fingerprint sem PII
                "member_keys": sorted(keys),
                "n_keys": len(keys),
            }
            for cpf, keys in sorted(cpf_collisions.items(), key=lambda kv: -len(kv[1]))[:5]
        ],
    }


def _summarize(index: dict) -> list[dict]:
    """Filtra CPFs com >1 member_key e formata workspaces afetados."""
    affected: list[dict] = []
    for workspace_id, cpf_map in sorted(index.items()):
        collisions = {cpf: keys for cpf, keys in cpf_map.items() if len(keys) > 1}
        if collisions:
            affected.append(_run_entry(workspace_id, collisions))
    return affected


def _connect(db_url: str):
    from sqlalchemy import create_engine

    if db_url.startswith("sqlite+aiosqlite:"):
        db_url = db_url.replace("sqlite+aiosqlite:", "sqlite:", 1)
    return create_engine(db_url)


def _fetch_patrimonio_rows(db_url: str):
    """Itera artifacts patrimoniais — E4.patrimonio + E1.5c.baseline_patrimonial."""
    from sqlalchemy import text

    engine = _connect(db_url)
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT workspace_id, pipeline_run_id, artifact_key, content_json "
                "FROM pipeline_artifacts "
                "WHERE (stage = 'E4' AND artifact_key = 'patrimonio') "
                "   OR (stage IN ('E1.5', 'E1.5c') AND artifact_key = 'baseline_patrimonial')"
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


def _run_audit(db_url: str, output_path: str) -> int:
    """Pipeline principal: fetch → index → summarize → emit."""
    rows = _fetch_patrimonio_rows(db_url)
    print(f"[audit] {len(rows)} patrimônio artifacts varridos", file=sys.stderr)
    affected = _summarize(_index_members(rows))
    print(f"[audit] {len(affected)} workspaces com CPF→member_key collision", file=sys.stderr)
    payload = json.dumps(
        {"affected_count": len(affected), "affected": affected}, indent=2, ensure_ascii=False
    )
    _emit(output_path, payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_argv(argv)
    if not args.db_url:
        print("error: --db-url ou MATHOMS_DATABASE_URL obrigatório", file=sys.stderr)
        return 2
    return _run_audit(args.db_url, args.output)


if __name__ == "__main__":
    sys.exit(main())
