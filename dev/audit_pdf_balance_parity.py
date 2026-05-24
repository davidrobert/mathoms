#!/usr/bin/env python3
"""Audita paridade saldo↔transações em E3 reconciled artifacts (perda silenciosa por bugs de parser)."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from backend.app.services.crypto import (  # noqa: E402
    decrypt_artifact_payload,
    is_encrypted_payload,
)

DEFAULT_DB = str(_REPO_ROOT / "mathoms.db")
DEFAULT_ABS_THRESHOLD = 50.0
DEFAULT_PCT_THRESHOLD = 0.01


def _is_fatura(payload: dict, artifact_key: str) -> bool:
    """Fatura tem saldo = valor a pagar (não delta de extrato); skipa por padrão."""
    if str(payload.get("tipo", "")).lower().startswith("fatura"):
        return True
    return "fatura" in (artifact_key or "").lower()


def _load_payload(con: sqlite3.Connection, art_id: int) -> dict | None:
    row = con.execute(
        "SELECT content_json FROM pipeline_artifacts WHERE id=?", (art_id,)
    ).fetchone()
    if not row:
        return None
    payload = json.loads(row["content_json"])
    if is_encrypted_payload(payload):
        payload = decrypt_artifact_payload(payload)
    return payload


def _sum_txs(txs: list[dict]) -> tuple[float, float]:
    """Retorna `(tx_sum, volume)` — `volume = creditos − debitos` (sem sinal)."""
    creditos = sum(float(t.get("valor", 0)) for t in txs if float(t.get("valor", 0)) > 0)
    debitos = sum(float(t.get("valor", 0)) for t in txs if float(t.get("valor", 0)) < 0)
    return creditos + debitos, creditos - debitos


def _saldo_delta_diff_pct(
    saldo_ini, saldo_fim, tx_sum: float, volume: float
) -> tuple[float | None, float | None, float | None]:
    """Calcula `(saldo_delta, diff, pct)`; retorna `(None, None, None)` se saldo ausente."""
    if saldo_ini is None or saldo_fim is None:
        return None, None, None
    delta = float(saldo_fim) - float(saldo_ini)
    diff = delta - tx_sum
    pct = abs(diff) / volume if volume > 0 else None
    return delta, diff, pct


def _compute_metrics(payload: dict) -> dict[str, Any]:
    """Paridade: `saldo_final - saldo_inicial == sum(transacoes.valor)`?"""
    txs = payload.get("transacoes", []) or []
    tx_sum, volume = _sum_txs(txs)
    saldo_ini, saldo_fim = payload.get("saldo_inicial"), payload.get("saldo_final")
    delta, diff, pct = _saldo_delta_diff_pct(saldo_ini, saldo_fim, tx_sum, volume)
    return {
        "n_txs": len(txs),
        "moeda": payload.get("moeda", "BRL"),
        "saldo_inicial": saldo_ini,
        "saldo_final": saldo_fim,
        "saldo_delta": delta,
        "tx_sum": tx_sum,
        "volume": volume,
        "diff": diff,
        "diff_pct": pct,
    }


def _classify(m: dict, abs_thr: float, pct_thr: float) -> str | None:
    """`paridade_quebrada` exige AMBOS thresholds estourados."""
    if m["n_txs"] == 0:
        return None
    if m["saldo_inicial"] is None or m["saldo_final"] is None:
        return "saldo_ausente"
    if m["diff"] is None or abs(m["diff"]) < abs_thr:
        return None
    if m["diff_pct"] is None or m["diff_pct"] < pct_thr:
        return None
    return "paridade_quebrada"


def _audit_one(
    con: sqlite3.Connection,
    art_id: int,
    artifact_key: str,
    abs_thr: float,
    pct_thr: float,
    include_fatura: bool,
) -> dict | None:
    """Audita 1 artifact E3. Retorna `None` se for fatura skipada/sem payload."""
    payload = _load_payload(con, art_id)
    if not payload or (not include_fatura and _is_fatura(payload, artifact_key)):
        return None
    m = _compute_metrics(payload)
    m["artifact_id"] = art_id
    m["artifact_key"] = artifact_key
    m["bank"] = (artifact_key or "").split("_", 1)[0]
    m["flag"] = _classify(m, abs_thr, pct_thr)
    return m


def audit_workspace(
    con: sqlite3.Connection,
    ws_id: str,
    abs_thr: float,
    pct_thr: float,
    include_fatura: bool,
) -> list[dict]:
    """Roda paridade em todos E3 reconciled do workspace."""
    rows = con.execute(
        "SELECT id, artifact_key FROM pipeline_artifacts "
        "WHERE workspace_id=? AND stage='E3' ORDER BY artifact_key",
        (ws_id,),
    ).fetchall()
    out = [
        _audit_one(con, r["id"], r["artifact_key"], abs_thr, pct_thr, include_fatura) for r in rows
    ]
    return [f for f in out if f is not None]


def _money(v) -> str:
    return "—" if v is None else f"{v:>14,.2f}"


def _pct(v) -> str:
    return "—" if v is None else f"{v * 100:>6.2f}%"


def _print_quebradas_table(quebradas: list[dict]) -> None:
    print(f"\n## Paridade quebrada ({len(quebradas)})\n")
    header = (
        f"{'banco':>15} | {'extrato_key':<50} | {'n_txs':>5} | {'moeda':>5} | "
        f"{'saldo_d':>14} | {'tx_sum':>14} | {'diff':>14} | {'pct':>7}"
    )
    print(header)
    print("-" * len(header))
    for f in sorted(quebradas, key=lambda x: -abs(x["diff"] or 0)):
        print(
            f"{f['bank']:>15} | {f['artifact_key'][:50]:<50} | "
            f"{f['n_txs']:>5} | {f['moeda']:>5} | "
            f"{_money(f['saldo_delta'])} | {_money(f['tx_sum'])} | "
            f"{_money(f['diff'])} | {_pct(f['diff_pct'])}"
        )


def _print_by_bank(quebradas: list[dict]) -> None:
    by_bank: dict[str, int] = defaultdict(int)
    for f in quebradas:
        by_bank[f["bank"]] += 1
    print("\n## Por banco:\n")
    for bank, n in sorted(by_bank.items(), key=lambda x: -x[1]):
        print(f"  {bank:>15}: {n}")


def print_report(findings: list[dict]) -> int:
    """Imprime relatório. Retorna 1 se paridade_quebrada, 0 senão."""
    by_flag = defaultdict(list)
    for f in findings:
        by_flag[f["flag"] or "ok"].append(f)
    print(f"\nTotal extratos auditados: {len(findings)}")
    for flag, items in sorted(by_flag.items(), key=lambda x: -len(x[1])):
        print(f"  {flag:>20}: {len(items)}")
    quebradas = by_flag["paridade_quebrada"]
    if not quebradas:
        print("\nNenhuma paridade quebrada detectada.")
        return 0
    _print_quebradas_table(quebradas)
    _print_by_bank(quebradas)
    return 1


def _resolve_workspaces(con: sqlite3.Connection, args: argparse.Namespace) -> list[str]:
    if args.workspace_id:
        return [args.workspace_id]
    return [r["id"] for r in con.execute("SELECT id FROM workspaces ORDER BY id").fetchall()]


def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Audita paridade saldo↔txs em E3.")
    ap.add_argument("--db", default=os.environ.get("MATHOMS_DB", DEFAULT_DB))
    ap.add_argument("--workspace-id", help="UUID; omitir = todos")
    ap.add_argument("--all-workspaces", action="store_true")
    ap.add_argument("--abs-threshold", type=float, default=DEFAULT_ABS_THRESHOLD)
    ap.add_argument("--pct-threshold", type=float, default=DEFAULT_PCT_THRESHOLD)
    ap.add_argument(
        "--include-fatura",
        action="store_true",
        help="Inclui faturas (default: ignora — semântica diferente)",
    )
    ap.add_argument("--json", help="Path pra dump JSON dos findings")
    return ap


def _collect_all_findings(
    con: sqlite3.Connection, ws_ids: list[str], args: argparse.Namespace
) -> list[dict]:
    out: list[dict] = []
    for ws_id in ws_ids:
        findings = audit_workspace(
            con, ws_id, args.abs_threshold, args.pct_threshold, args.include_fatura
        )
        for f in findings:
            f["ws_id"] = ws_id
        out.extend(findings)
    return out


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if not os.environ.get("MATHOMS_FERNET_KEY"):
        sys.stderr.write("ERROR: export MATHOMS_FERNET_KEY antes de rodar.\n")
        return 2
    if not Path(args.db).exists():
        sys.stderr.write(f"ERROR: DB nao encontrado: {args.db}\n")
        return 2
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    ws_ids = _resolve_workspaces(con, args)
    print(f"# Auditoria paridade saldo↔transacoes — {len(ws_ids)} workspace(s)")
    findings = _collect_all_findings(con, ws_ids, args)
    exit_code = print_report(findings)
    if args.json:
        Path(args.json).write_text(json.dumps(findings, indent=2, ensure_ascii=False, default=str))
        print(f"\nJSON dump: {args.json}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
