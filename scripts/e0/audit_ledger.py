"""Checks 4, 5 — ledger e saldo (A6g.2 — T1.c)."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from scripts.e0 import audit_helpers as _h


def check_inbox_log() -> list[dict[str, Any]]:
    """Check inbox_log.md for suspicious renames (original ≠ final name)."""
    issues: list[dict[str, Any]] = []

    if not _h.INBOX_LOG.exists():
        issues.append(
            {"file": "inbox_log.md", "issue": "Arquivo não encontrado", "severity": "INFO"}
        )
        return issues

    text = _h.INBOX_LOG.read_text(encoding="utf-8")

    # Parse detalhamento table rows: | # | Nome original | Nome final | Destino | Status |
    # Only process lines after "### Detalhamento" and match rows where:
    # - First column is a plain integer
    # - Nome fields look like filenames (contain a dot or dash)
    detalhamento_section = text.split("### Detalhamento")[-1] if "### Detalhamento" in text else ""
    pattern = r"\|\s*(\d+)\s*\|\s*(\S+\.\S+)\s*\|\s*(\S+\.\S+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
    raw_matches = re.findall(pattern, detalhamento_section)
    matches = [(m[1], m[2], m[3], m[4]) for m in raw_matches]

    for original, final, destino, status in matches:
        original = original.strip()
        final = final.strip()

        if original != final:
            issues.append(
                {
                    "file": final,
                    "issue": f"Renomeado no inbox: '{original}' → '{final}'",
                    "severity": "INFO",
                    "original_name": original,
                    "final_name": final,
                }
            )

    return issues


def check_saldo_gaps() -> list[dict[str, Any]]:
    """Check E3 reconciled files for saldo discontinuities across periods
    of the same account (saldo_final of period N ≠ saldo_inicial of period N+1)."""
    issues: list[dict[str, Any]] = []

    e3_dir = _h.PROJECT_DIR / "processed" / "E3_reconciled"
    if not e3_dir.is_dir():
        return issues

    # Group by (banco, tipo_conta, moeda)
    accounts: dict[tuple, list] = defaultdict(list)

    for fpath in sorted(e3_dir.glob("*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        if "_tombstone" in data:
            continue

        banco = data.get("banco", "")
        tipo = data.get("tipo_conta", "")
        moeda = data.get("moeda", "")
        periodo = data.get("periodo_cobertura", {})
        saldo_i = data.get("saldo_inicial")
        saldo_f = data.get("saldo_final")

        if saldo_i is None and saldo_f is None:
            continue

        key = (_h.normalize(banco), _h.normalize(tipo), _h.normalize(moeda))
        accounts[key].append(
            {
                "file": fpath.name,
                "inicio": periodo.get("inicio", ""),
                "fim": periodo.get("fim", ""),
                "saldo_inicial": saldo_i,
                "saldo_final": saldo_f,
            }
        )

    # For each account, sort by period start and check continuity
    for key, entries in sorted(accounts.items()):
        sorted_entries = sorted(entries, key=lambda e: e["inicio"])

        for i in range(len(sorted_entries) - 1):
            curr = sorted_entries[i]
            nxt = sorted_entries[i + 1]

            if curr["saldo_final"] is None or nxt["saldo_inicial"] is None:
                continue

            try:
                diff = abs(float(nxt["saldo_inicial"]) - float(curr["saldo_final"]))
            except (ValueError, TypeError):
                continue

            if diff > 0.01:  # tolerance for rounding
                issues.append(
                    {
                        "file": f"{curr['file']} → {nxt['file']}",
                        "issue": (
                            f"Gap de saldo: {key[0]}/{key[1]} ({key[2]}) — "
                            f"fim {curr['fim']} = {curr['saldo_final']}, "
                            f"início {nxt['inicio']} = {nxt['saldo_inicial']} "
                            f"(diff: {diff:.2f})"
                        ),
                        "severity": "WARNING",
                    }
                )

    return issues


__all__ = [
    "check_inbox_log",
    "check_saldo_gaps",
]
