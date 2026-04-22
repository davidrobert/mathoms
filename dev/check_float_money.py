#!/usr/bin/env python3
"""A6g.6 slice 3 · ADR-114 — bloqueia `: float` em campo monetário (ADR-090).

Regra: dinheiro nunca é float. Use Money.brl(...)/Decimal em Python;
int64 cents em Go; string decimal no wire.

Detecção: linhas ADICIONADAS em `git diff --cached` que declaram um
campo com nome contendo amount|valor|brl|saldo|money|total|price|cost
e anotação `: float`. Legado (79 ofensores em A6g.1) fica fora — só
blocamos código NOVO.

Skip explícito: docstring/comentário inline dizendo "percentage", "rate",
"tolerance" ou "tolerância" desqualifica (não é money, é razão/threshold).

Chamado via pre-commit `pass_filenames: true`; exit 0 se não há staged
ou nenhum viola. Exit 1 mostrando arquivo + linha ofensora.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Tokens monetários — case-insensitive match no nome do campo.
MONEY_TOKENS = re.compile(
    r"(amount|valor|brl|saldo|money|total|price|cost|despesa|receita|"
    r"aporte|patrimonio|capital|dinheiro|preco)",
    re.IGNORECASE,
)
# Campo tipado com float puro (não list[float]/tuple[float,...]).
FIELD_FLOAT = re.compile(r"^\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*:\s*float\b(?!\s*\|)")
# Exceções (tolerâncias, taxas, percentuais) — skip se linha contém esses tokens.
SKIP_TOKENS = re.compile(
    r"(percentage|percentual|rate|taxa|tolerance|tolera|threshold|limite|"
    r"ratio|fator|factor)",
    re.IGNORECASE,
)


def get_added_lines_for(file_path: str) -> list[tuple[int, str]]:
    """Return [(line_no_new, content)] for lines ADDED in staged diff."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "-U0", "--", file_path],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return []
    added: list[tuple[int, str]] = []
    new_ln = 0
    hunk_header = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for line in out.splitlines():
        m = hunk_header.match(line)
        if m:
            new_ln = int(m.group(1))
            continue
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            added.append((new_ln, line[1:]))
            new_ln += 1
        elif not line.startswith("-"):
            new_ln += 1
    return added


def check_file(file_path: str) -> list[tuple[int, str, str]]:
    """Return [(line_no, field_name, content)] of money-float offenders in staged diff."""
    offenders: list[tuple[int, str, str]] = []
    for line_no, content in get_added_lines_for(file_path):
        if SKIP_TOKENS.search(content):
            continue
        m = FIELD_FLOAT.match(content)
        if not m:
            continue
        field_name = m.group(1)
        if MONEY_TOKENS.search(field_name):
            offenders.append((line_no, field_name, content.rstrip()))
    return offenders


def main(argv: list[str]) -> int:
    all_offenders: list[tuple[str, int, str, str]] = []
    for arg in argv:
        p = Path(arg)
        if p.suffix != ".py":
            continue
        for line_no, name, content in check_file(arg):
            all_offenders.append((arg, line_no, name, content))
    if not all_offenders:
        return 0
    print("ERRO: `: float` em campo monetário — violação do ADR-090:", file=sys.stderr)
    for file_path, line_no, name, content in all_offenders:
        print(f"  {file_path}:{line_no} — {name}", file=sys.stderr)
        print(f"    {content.strip()}", file=sys.stderr)
    print(
        "\nRegra ADR-090: dinheiro nunca é float.\n"
        "  Python:  use Money.brl(...)  ou  Decimal(str(v))\n"
        "  Wire:    string decimal\n"
        "  Go:      int64 cents\n"
        "Se for tolerância/taxa/razão (não money), renomeie ou adicione\n"
        "comentário com 'rate|percentage|tolerance' na mesma linha.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
