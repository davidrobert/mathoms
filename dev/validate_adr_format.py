#!/usr/bin/env python3
"""Valida formato de ADRs em docs/DECISIONS.md.

Confere por ADR:
- heading: `## ADR-NNN — Título` (3 dígitos zero-padded; sufixo `-XX`
  aceito apenas para ADR-029-TQ e ADR-030-WS, que são históricas);
- linha de Status no formato:
    `**Status:** {Decidido | Proposto | Roadmap} • **Data:** YYYY-MM-DD ...`
  (suffixos de fase em parênteses são preservados; texto extra após
  `• **Data:**` é livre — encerramento, supersedure, etc.);
- ADRs com >20 linhas devem ter pelo menos uma das seções:
  `**Contexto**`, `**Decisão**` ou `**Consequências**` (curtas estub
  F0-F7 ficam isentas).

Uso:
    python3 dev/validate_adr_format.py        # exit 1 se houver violação
    python3 dev/validate_adr_format.py -v     # verbose (lista ADRs OK)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS = REPO_ROOT / "docs" / "DECISIONS.md"

ALLOWED_STATUS = {"Decidido", "Proposto", "Roadmap"}
HEADING_RE = re.compile(r"^## (ADR-([0-9]+(?:-[A-Z]+)?)) — (.+)$")
STATUS_RE = re.compile(
    r"^\*\*Status:\*\*\s+(?:~~)?(?P<status>[A-Za-zÁ-ÿ]+)"
)
DATE_RE = re.compile(r"\*\*Data:\*\*\s*(\d{4}-\d{2}-\d{2})")

STUB_THRESHOLD_LINES = 20
SECTION_PROBES = ("**Contexto", "**Decisão", "**Consequências", "**Decision", "**Consequences")


def parse_adrs(content: str) -> list[dict]:
    """Quebra o arquivo em blocos por ADR e retorna metadados."""
    lines = content.splitlines()
    adrs: list[dict] = []
    current: dict | None = None
    for i, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            if current is not None:
                current["end_line"] = i - 1
                adrs.append(current)
            current = {
                "id": m.group(1),
                "id_num": m.group(2),
                "title": m.group(3),
                "start_line": i,
                "end_line": i,
                "status_line": None,
                "status_value": None,
                "date_value": None,
                "body_lines": [],
            }
        elif current is not None:
            current["body_lines"].append(line)
            if current["status_line"] is None:
                sm = STATUS_RE.match(line)
                if sm:
                    current["status_line"] = line
                    current["status_value"] = sm.group("status")
                    dm = DATE_RE.search(line)
                    if dm:
                        current["date_value"] = dm.group(1)
    if current is not None:
        current["end_line"] = len(lines)
        adrs.append(current)
    return adrs


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
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--file",
        type=Path,
        default=DECISIONS,
        help="Caminho do markdown (default: docs/DECISIONS.md)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    content = args.file.read_text(encoding="utf-8")
    adrs = parse_adrs(content)
    print(f"docs/DECISIONS.md — {len(adrs)} ADRs")

    total_problems = 0
    ok_count = 0
    for adr in adrs:
        problems = validate(adr)
        if not problems:
            ok_count += 1
            if args.verbose:
                print(f"  ✓ L{adr['start_line']:5d} {adr['id']}")
            continue
        total_problems += len(problems)
        print(f"\n  ✗ L{adr['start_line']} {adr['id']} — {adr['title']}")
        for p in problems:
            print(f"    - {p}")

    print(f"\n{ok_count}/{len(adrs)} OK · {total_problems} violação(ões)")
    return 0 if total_problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
