#!/usr/bin/env python3
"""Snapshot de selecao E2 + baseline da rodada unificada, e o diff que o julga."""

# O runbook (§5 F1/F2) exige IDENTIDADE entre o mapa pre-run e o pos-run:
# `{(stage, artifact_key) -> (id, byte_size)}`, colapsado no mais recente.
#
# O modo `--compare` existe porque o `U3` publicou `E2 ✅` sobre um predicado que
# REPROVA — leu o delta como ruido. Aqui o veredito e sobre o mapa inteiro e
# nomeia cada unidade divergente, e o exit code impede a leitura otimista.
#
#     dev/unified_e2_snapshot.py <workspace_id> [--db mathoms.db]
#     dev/unified_e2_snapshot.py --compare <pre.json> <pos.json>

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

STAGES = ("consolidate_baseline", "extract_invoices", "extract_statements", "extract_with_llm")


def snapshot(workspace_id: str, db_path: str) -> dict[str, dict[str, object]]:
    """Mapa {stage|artifact_key -> {id, byte_size}}, ultimo por chave (ORDER BY id)."""
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            f"SELECT stage, artifact_key, id, byte_size FROM pipeline_artifacts "
            f"WHERE workspace_id=? AND stage IN ({','.join('?' * len(STAGES))}) ORDER BY id",
            (workspace_id, *STAGES),
        ).fetchall()
    finally:
        con.close()
    snap: dict[str, dict[str, object]] = {}
    for stage, key, artifact_id, byte_size in rows:
        snap[f"{stage}|{key}"] = {"id": artifact_id, "byte_size": byte_size}
    return dict(sorted(snap.items()))


def compare(pre: dict, pos: dict) -> dict[str, object]:
    """Diff nomeado. `identico` e o veredito do runbook; as listas o falsificam."""
    only_pre = sorted(set(pre) - set(pos))
    only_pos = sorted(set(pos) - set(pre))
    mudadas = [
        {"chave": k, "pre": pre[k], "pos": pos[k]}
        for k in sorted(set(pre) & set(pos))
        if pre[k] != pos[k]
    ]
    return {
        "n_pre": len(pre),
        "n_pos": len(pos),
        "identico": not (only_pre or only_pos or mudadas),
        "removidas": only_pre,
        "acrescentadas": only_pos,
        "mudadas": mudadas,
    }


def _print_compare(resultado: dict[str, object]) -> int:
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    if resultado["identico"]:
        print("\nE2: PASS — mapa identico", file=sys.stderr)
        return 0
    n = len(resultado["removidas"]) + len(resultado["acrescentadas"]) + len(resultado["mudadas"])
    print(
        f"\nE2: REPROVA — {n} unidade(s) divergente(s); o corpus mudou sob a medicao",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_id", nargs="?")
    parser.add_argument("--db", default="mathoms.db")
    parser.add_argument("--compare", nargs=2, metavar=("PRE", "POS"))
    args = parser.parse_args()

    if args.compare:
        pre = json.loads(Path(args.compare[0]).read_text())
        pos = json.loads(Path(args.compare[1]).read_text())
        return _print_compare(compare(pre, pos))

    if not args.workspace_id:
        parser.error("workspace_id e obrigatorio fora do modo --compare")
    print(json.dumps(snapshot(args.workspace_id, args.db), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
