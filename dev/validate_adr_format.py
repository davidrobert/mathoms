#!/usr/bin/env python3
"""Valida formato de ADRs em docs/DECISIONS.md (heading + Status/Data + seções mínimas)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS = REPO_ROOT / "docs" / "DECISIONS.md"

ALLOWED_STATUS = {"Decidido", "Proposto", "Roadmap"}
HEADING_RE = re.compile(r"^## (ADR-([0-9]+(?:-[A-Z]+)?)) — (.+)$")
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s+(?:~~)?(?P<status>[A-Za-zÁ-ÿ]+)")
DATE_RE = re.compile(r"\*\*Data:\*\*\s*(\d{4}-\d{2}-\d{2})")

STUB_THRESHOLD_LINES = 20
SECTION_PROBES = ("**Contexto", "**Decisão", "**Consequências", "**Decision", "**Consequences")


def parse_adrs(content: str) -> list[dict]:
    """Quebra o arquivo em blocos por ADR e retorna metadados."""
    lines = content.splitlines()
    adrs: list[dict] = []
    current: dict | None = None
    for i, line in enumerate(lines, start=1):
        current = _process_line(line, i, current, adrs)
    if current is not None:
        current["end_line"] = len(lines)
        adrs.append(current)
    return adrs


def _process_line(line: str, line_no: int, current: dict | None, adrs: list[dict]) -> dict | None:
    m = HEADING_RE.match(line)
    if m:
        if current is not None:
            current["end_line"] = line_no - 1
            adrs.append(current)
        return _new_adr_record(m, line_no)
    if current is not None:
        _append_body_line(current, line)
    return current


def _new_adr_record(match: re.Match, line_no: int) -> dict:
    return {
        "id": match.group(1),
        "id_num": match.group(2),
        "title": match.group(3),
        "start_line": line_no,
        "end_line": line_no,
        "status_line": None,
        "status_value": None,
        "date_value": None,
        "body_lines": [],
    }


def _append_body_line(current: dict, line: str) -> None:
    current["body_lines"].append(line)
    if current["status_line"] is not None:
        return
    sm = STATUS_RE.match(line)
    if sm is None:
        return
    current["status_line"] = line
    current["status_value"] = sm.group("status")
    dm = DATE_RE.search(line)
    if dm:
        current["date_value"] = dm.group(1)


def validate(adr: dict) -> list[str]:
    """Retorna lista de problemas (vazia ⇒ OK)."""
    problems: list[str] = []

    # 1. heading: ADR-NNN com 3 dígitos
    id_num_clean = adr["id_num"].split("-", 1)[0]
    if len(id_num_clean) != 3:
        problems.append(
            f"id `{adr['id']}` não tem 3 dígitos zero-padded "
            f"(deveria ser `ADR-{int(id_num_clean):03d}`)"
        )

    # 2. linha de Status presente
    if adr["status_line"] is None:
        # ADRs estub muito curtas podem omitir Status — contar linhas
        non_blank = sum(1 for line in adr["body_lines"] if line.strip())
        if non_blank > 5:
            problems.append("falta linha `**Status:** ...`")
        return problems

    # 3. valor de Status no vocabulário canônico
    if adr["status_value"] not in ALLOWED_STATUS:
        problems.append(
            f"Status `{adr['status_value']}` fora do vocabulário "
            f"{sorted(ALLOWED_STATUS)} (linha: {adr['status_line']!r})"
        )

    # 4. ADRs longas precisam de seções estruturadas
    body_lines = len(adr["body_lines"])
    if body_lines > STUB_THRESHOLD_LINES:
        body_text = "\n".join(adr["body_lines"])
        if not any(probe in body_text for probe in SECTION_PROBES):
            problems.append(
                f"ADR longa ({body_lines} linhas) sem seções "
                f"`**Contexto**`/`**Decisão**`/`**Consequências**`"
            )

    return problems


def main() -> int:
    args = _parse_args()
    content = args.file.read_text(encoding="utf-8")
    adrs = parse_adrs(content)
    print(f"docs/DECISIONS.md — {len(adrs)} ADRs")
    ok_count, total_problems = _report_violations(adrs, verbose=args.verbose)
    print(f"\n{ok_count}/{len(adrs)} OK · {total_problems} violação(ões)")
    return 0 if total_problems == 0 else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--file", type=Path, default=DECISIONS)
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def _report_violations(adrs: list[dict], *, verbose: bool) -> tuple[int, int]:
    total_problems = 0
    ok_count = 0
    for adr in adrs:
        problems = validate(adr)
        if not problems:
            ok_count += 1
            _maybe_print_ok(adr, verbose=verbose)
            continue
        total_problems += len(problems)
        _print_violations(adr, problems)
    return ok_count, total_problems


def _maybe_print_ok(adr: dict, *, verbose: bool) -> None:
    if verbose:
        print(f"  ✓ L{adr['start_line']:5d} {adr['id']}")


def _print_violations(adr: dict, problems: list[str]) -> None:
    print(f"\n  ✗ L{adr['start_line']} {adr['id']} — {adr['title']}")
    for p in problems:
        print(f"    - {p}")


if __name__ == "__main__":
    sys.exit(main())
