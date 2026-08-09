#!/usr/bin/env python3
"""Exige que `ADR-NNN` citado em prosa resolva para nota em `docs/adr/` (A40.l23)."""
# Reserva de ID por menção em prosa é invisível aos gates: `check_doc_links.py`
# só enxerga wikilink, e o alocador de ID é `ls docs/adr/ | tail`. A A39 citou
# "ADR-345" 6× em prosa sem escrever o arquivo — o ID ficou roubável até a
# [[ADR-345]] fechar a instância. Este gate fecha a classe.

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
ADR_DIR = DOCS / "adr"

# Congelados por design, não superfície de reserva nova: o shim preserva âncoras
# de PRs antigos, e `archive/` cita ADRs de planos substituídos.
WHITELIST_RE = re.compile(r"^docs/(DECISIONS\.md$|archive/)")

FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
WIKILINK_RE = re.compile(r"\[\[[^\]\n]*?\]\]")
ADR_REF_RE = re.compile(r"\bADR-(\d{3})\b")


def known_adr_numbers(adr_dir: Path = ADR_DIR) -> set[str]:
    """Números com arquivo em `docs/adr/` — o mesmo conjunto que `ls | tail` aloca."""
    return {p.name[:3] for p in adr_dir.glob("*.md") if p.name[:3].isdigit()}


def is_whitelisted(path: Path) -> bool:
    """Shim de âncoras históricas e arqueologia não disparam."""
    try:
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return False
    return WHITELIST_RE.match(rel) is not None


def _prose_lines(text: str) -> list[tuple[int, str]]:
    """Linhas fora de code fence, com wikilink e inline code removidos."""
    out: list[tuple[int, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((lineno, INLINE_CODE_RE.sub("", WIKILINK_RE.sub("", line))))
    return out


def unresolved_refs(path: Path, known: set[str]) -> list[tuple[int, str]]:
    """Refs `ADR-NNN` em prosa cujo número não tem arquivo. Vazio se whitelisted."""
    if is_whitelisted(path):
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [
        (lineno, m.group(0))
        for lineno, line in _prose_lines(text)
        for m in ADR_REF_RE.finditer(line)
        if m.group(1) not in known
    ]


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _targets(args: argparse.Namespace) -> list[Path]:
    if args.all:
        return sorted(DOCS.rglob("*.md"))
    return [Path(f) for f in args.filenames]


RESERVA_HINT = (
    "Nunca reserve ID de ADR; reserve o trabalho (CLAUDE.md §ADRs): use "
    "§Deferimento datado com dono no plano, ou escreva a nota `Roadmap` COM "
    "corpo. Se a ADR existe com outro número, corrija a citação."
)


def _print_offenders(offenders: list[tuple[Path, list[tuple[int, str]]]]) -> int:
    """Imprime `path:linha` + motivo por hit; devolve o total impresso."""
    total = 0
    for path, hits in offenders:
        for lineno, ref in hits:
            total += 1
            print(f"X {_rel(path)}:{lineno}")
            print(f"  {ref} citada em prosa não resolve para arquivo em docs/adr/.")
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("--all", action="store_true", help="varre docs/ inteiro")
    args = parser.parse_args(argv)

    known = known_adr_numbers()
    offenders = [(p, hits) for p in _targets(args) if (hits := unresolved_refs(p, known))]
    total = _print_offenders(offenders)
    if total:
        print(f"\n{total} referência(s) de ADR em prosa sem arquivo.\n{RESERVA_HINT}")
        return 1
    print(f"✓ referências de ADR em prosa resolvem ({len(known)} ADRs em docs/adr/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
