#!/usr/bin/env python3
"""Move seções de registro fechado do `_README` de uma sprint para `_HISTORY.md`."""
# Companheiro de `dev/check_sprint_readme_size.py`: o gate diz que a sprint
# precisa separar histórico, este script faz a separação.
#
# `--dry-run` LISTA candidatos e não move nada. O move exige `--section` por
# nome, uma decisão humana por seção — heurística que move sozinha erra no caso
# que importa (a seção que parece histórica e ainda governa decisão), e o custo
# de errar é apagar contexto de quem vai pegar a lane.
#
# O que este script NUNCA faz: reescrever, resumir ou apagar. Snapshot datado
# que alguém "atualiza" deixa de ser evidência. Cada seção movida deixa
# ponteiro no lugar de origem.

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPRINT_DIR = REPO_ROOT / "docs" / "sprint"

H2_SPLIT_RE = re.compile(r"(?m)^(## .+)$")

HEADER_TEMPLATE = """---
id: MOC-{slug}-historico
type: moc
title: "Sprint {sprint} — histórico: o que foi decidido, medido e encerrado"
aliases: ["{sprint} histórico"]
date: "{today}"
---

# Sprint {sprint} — histórico

> **Registro fechado, separado do `_README` em {today}.** Cada seção aqui é
> pendência **resolvida**, entrega **feita**, painel **encerrado** ou snapshot
> **datado** que o próprio texto manda não reescrever. Nada aqui governa
> decisão de hoje — o que governa ficou em [`_README`](_README.md).
>
> **Não apague, não reescreva.** Snapshot datado que alguém "atualiza" deixa de
> ser evidência.

"""

# `MOC-sprint-<x>` casa `_SPRINT_MOC_ID_RE` de build_doc_index e faria o índice
# listar o histórico como se fosse uma sprint. Daí `MOC-<x>-historico`.
POINTER_TEMPLATE = (
    "## {label}\n\n"
    "> Movida para [`_HISTORY`](_HISTORY.md) em {today} — registro fechado,\n"
    "> não governa decisão de hoje.\n\n"
)

HISTORICAL_HINTS = (
    "não o reescreva",
    "não os reescreva",
    "fica como registro",
    "é medição datada",
    "resolvida",
    "✅ **resolvida",
)


def _sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """(preâmbulo, [(título h2, corpo)])."""
    parts = H2_SPLIT_RE.split(text)
    return parts[0], list(zip(parts[1::2], parts[2::2]))


def _looks_historical(title: str, body: str) -> bool:
    lowered = (title + body).lower()
    return any(hint in lowered for hint in HISTORICAL_HINTS)


def _label(title: str) -> str:
    return title[3:].strip()


def _readme_of(sprint: str) -> Path:
    return SPRINT_DIR / sprint / "_README.md"


def list_candidates(sprint: str) -> list[tuple[str, int, bool]]:
    """(label, linhas, parece histórica) por seção h2 do `_README`."""
    _preamble, sections = _sections(_readme_of(sprint).read_text(encoding="utf-8"))
    return [
        (_label(title), len(body.splitlines()), _looks_historical(title, body))
        for title, body in sections
    ]


def _render_history(sprint: str, today: str, moved: list[tuple[str, str]], existing: str) -> str:
    body = "".join(title + section for title, section in moved)
    if existing:
        return existing.rstrip("\n") + "\n\n" + body
    slug = sprint.lower()
    return HEADER_TEMPLATE.format(sprint=sprint, slug=slug, today=today) + body


def split(sprint: str, wanted: list[str], today: str) -> tuple[int, int]:
    """Move as seções nomeadas. Devolve (nº movidas, linhas movidas)."""
    readme = _readme_of(sprint)
    history = readme.parent / "_HISTORY.md"
    preamble, sections = _sections(readme.read_text(encoding="utf-8"))
    kept, moved = [preamble], []
    for title, body in sections:
        if _label(title) in wanted:
            moved.append((title, body))
            kept.append(POINTER_TEMPLATE.format(label=_label(title), today=today))
        else:
            kept.append(title + body)
    if not moved:
        return (0, 0)
    existing = history.read_text(encoding="utf-8") if history.is_file() else ""
    history.write_text(_render_history(sprint, today, moved, existing), encoding="utf-8")
    readme.write_text("".join(kept), encoding="utf-8")
    return (len(moved), sum(len(body.splitlines()) for _t, body in moved))


def _print_candidates(sprint: str) -> int:
    rows = list_candidates(sprint)
    if not rows:
        print(f"{sprint}: nenhum h2 no `_README`.", file=sys.stderr)
        return 1
    print(f"{sprint} — seções do `_README` ({sum(n for _l, n, _h in rows)} linhas em h2):\n")
    for label, lines, historical in sorted(rows, key=lambda r: -r[1]):
        mark = "histórica?" if historical else "          "
        print(f"  {lines:5d}  {mark}  {label}")
    print("\nMover: --section '<label>' (repetível). Nada é movido sem --section.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--sprint", required=True, help="id da sprint, ex.: A40")
    parser.add_argument("--dry-run", action="store_true", help="lista candidatos, não move")
    parser.add_argument("--section", action="append", default=[], help="label h2 a mover")
    parser.add_argument("--today", required=False, help="data ISO do registro (default: hoje)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not _readme_of(args.sprint).is_file():
        print(f"{args.sprint}: docs/sprint/{args.sprint}/_README.md não existe.", file=sys.stderr)
        return 2
    if args.dry_run or not args.section:
        return _print_candidates(args.sprint)
    from datetime import date

    today = args.today or date.today().isoformat()
    count, lines = split(args.sprint, args.section, today)
    if not count:
        print("nenhuma seção casou os --section informados.", file=sys.stderr)
        return 1
    print(f"movidas {count} seções ({lines} linhas) para docs/sprint/{args.sprint}/_HISTORY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
