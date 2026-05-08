#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev/check_sigilo_terms.py — hook §13 sigilo metodológico.

Mathoms não tem licença/autorização das obras, marcas pessoais ou cursos de
Bruno Perini (Viver de Renda), Gustavo Cerbasi (Equilíbrio Financeiro /
Casais Inteligentes), Raul Sena (AUVP). Uso público desses nomes/marcas em
copy renderizada ao usuário (UI cliente, relatório, e-mail, PDF, landing) é
violação de marca pessoal/curso.

Política completa: docs/reference/COPY_GUIDELINES.md §13.
Substituições canônicas: §13.2.

Atribuição **interna** (filenames, types, ids, docstrings, comentários,
config rationale) é PERMITIDA — §13.4. Por isso este hook:

  1. Restringe surface a `frontend/src/app/` + `frontend/src/components/`
     (paths user-facing).
  2. Exclui paths internal-only conhecidos (types, api contract, generated,
     dev playground, variant-key components, barrel exports).
  3. Strip comentários (block `/* */` + line `//`) antes do grep — atribuição
     em docstring permanece OK.
  4. Match case-sensitive com word boundaries: `Cerbasi` (capital C) bloqueia
     "Visão Cerbasi" mas não `tone="cerbasi"` (variant key) nem
     `EquilibrioCerbasiCard` (identifier).

Uso:
  python3 dev/check_sigilo_terms.py [<file> ...]   # checa arquivos passados
  python3 dev/check_sigilo_terms.py --all          # scan completo do repo

Retorna exit 0 se zero hits user-facing; exit 1 se hits encontrados.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Padrões de detecção — case-sensitive com word boundary.
# Lowercase variants ("cerbasi" em variant key) NÃO são flagged: o risco
# legal é sobre proper-noun branding, não substring de identifier.
# ---------------------------------------------------------------------------
FORBIDDEN_RE = re.compile(
    r"\b("
    r"Bruno\s+Perini"
    r"|Gustavo\s+Cerbasi"
    r"|Raul\s+Sena"
    r"|Viver\s+de\s+Renda"
    r"|Equilíbrio\s+Financeiro"
    r"|Casais\s+Inteligentes"
    r"|Perini"
    r"|Cerbasi"
    r"|AUVP"
    r")\b"
)

# Substituições canônicas — manter em sync com §13.2 do COPY_GUIDELINES.md.
SUBSTITUTIONS = {
    "Bruno Perini": "remover atribuição — pilar 'patrimônio gerador de renda'",
    "Gustavo Cerbasi": "remover atribuição — pilar 'equilíbrio entre presente e futuro'",
    "Raul Sena": "remover atribuição — pilar 'alocação contracíclica + análise fundamentalista'",
    "Viver de Renda": "patrimônio gerador de renda / renda passiva sustentada",
    "Equilíbrio Financeiro": "equilíbrio entre presente e futuro / balanço presente-futuro",
    "Casais Inteligentes": "decisão financeira a quatro mãos / planejamento patrimonial do casal",
    "Perini": "padrão consagrado de planejamento patrimonial brasileiro",
    "Cerbasi": "(remover) — descreva o conceito sem atribuir",
    "AUVP": "alocação contracíclica / estratégia adaptativa à curva de juros",
}

# ---------------------------------------------------------------------------
# Surface user-facing — arquivos onde o hook FAIL se encontrar termos.
# ---------------------------------------------------------------------------
USER_FACING_PREFIXES = (
    "frontend/src/app/",
    "frontend/src/components/",
)
USER_FACING_SUFFIXES = (".tsx", ".ts")

# Exclusões — paths internal-only por convenção (§13.4 atribuição PERMITIDA).
EXCLUDED_PREFIXES = ("frontend/src/app/(app)/reports/_dev/",)
EXCLUDED_FILES = frozenset(
    {
        # Variant key "cerbasi" como literal técnico, não user-facing.
        "frontend/src/components/report/ui/NotasInsightsGrid.tsx",
        # Barrel exports — re-exporta nomes de componentes internos.
        "frontend/src/components/report/cards/index.ts",
    }
)

# ---------------------------------------------------------------------------
# Comment stripping — atribuição em docstring é permitida (§13.4).
# Ordem importa: block primeiro, depois line.
# ---------------------------------------------------------------------------
BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/", re.MULTILINE)
LINE_COMMENT_RE = re.compile(r"//[^\n]*", re.MULTILINE)


def is_user_facing(rel_path: str) -> bool:
    """True se rel_path é user-facing e não excluído."""
    if not rel_path.endswith(USER_FACING_SUFFIXES):
        return False
    if not any(rel_path.startswith(p) for p in USER_FACING_PREFIXES):
        return False
    if any(rel_path.startswith(p) for p in EXCLUDED_PREFIXES):
        return False
    if rel_path in EXCLUDED_FILES:
        return False
    return True


def strip_comments(content: str) -> str:
    """Remove block + line comments. Preserva número de linhas (substitui
    block por quebras) para line numbers nos hits permanecerem precisos."""

    def block_to_lines(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    no_block = BLOCK_COMMENT_RE.sub(block_to_lines, content)
    return LINE_COMMENT_RE.sub("", no_block)


def _scan_for_hits(
    stripped_lines: list[str], original_lines: list[str]
) -> list[tuple[int, str, str]]:
    """Itera linhas e coleta matches do regex em hits brutos."""
    hits: list[tuple[int, str, str]] = []
    for line_idx, stripped_line in enumerate(stripped_lines):
        for match in FORBIDDEN_RE.finditer(stripped_line):
            term = match.group(1)
            line_no = line_idx + 1
            original = original_lines[line_idx] if line_idx < len(original_lines) else ""
            hits.append((line_no, term, original.rstrip()))
    return hits


def _dedupe(hits: list[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
    """Remove duplicatas (line, term)."""
    seen: set[tuple[int, str]] = set()
    unique: list[tuple[int, str, str]] = []
    for hit in hits:
        key = (hit[0], hit[1])
        if key not in seen:
            seen.add(key)
            unique.append(hit)
    return unique


def check_file(path: Path) -> list[tuple[int, str, str]]:
    """Returns [(line_number, matched_term, line_content)] para hits user-facing."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    stripped = strip_comments(content)
    raw_hits = _scan_for_hits(stripped.splitlines(), content.splitlines())
    return _dedupe(raw_hits)


def _collect_all_user_facing() -> list[Path]:
    """rglob em todas as user-facing prefixes."""
    candidates: list[Path] = []
    for prefix in USER_FACING_PREFIXES:
        base = REPO_ROOT / prefix
        if not base.exists():
            continue
        for suffix in USER_FACING_SUFFIXES:
            candidates.extend(base.rglob(f"*{suffix}"))
    return sorted(p for p in candidates if p.is_file())


def collect_files(args_files: list[str], scan_all: bool) -> list[Path]:
    """Resolve lista de arquivos a checar."""
    if scan_all:
        return _collect_all_user_facing()
    files: list[Path] = []
    for fname in args_files:
        p = Path(fname)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.is_file():
            files.append(p)
    return files


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _print_header() -> None:
    print("", file=sys.stderr)
    print("=" * 72, file=sys.stderr)
    print("§13 sigilo metodológico (LEGAL/IP) — termos proibidos detectados em", file=sys.stderr)
    print(
        "superfície user-facing. Mathoms não tem licença para citar essas marcas", file=sys.stderr
    )
    print("publicamente.", file=sys.stderr)
    print("=" * 72, file=sys.stderr)


def _print_file_hits(path: Path, hits: list[tuple[int, str, str]]) -> None:
    print(f"\n  {relpath(path)}", file=sys.stderr)
    for line_no, term, line in hits:
        suggestion = SUBSTITUTIONS.get(term, "(ver §13.2 COPY_GUIDELINES)")
        print(f"    L{line_no}: '{term}' detectado", file=sys.stderr)
        print(f"      > {line.strip()}", file=sys.stderr)
        print(f"      → sugestão: {suggestion}", file=sys.stderr)


def _print_footer() -> None:
    print("", file=sys.stderr)
    print("Atribuição interna (filenames, types, ids, docstrings, comentários) é", file=sys.stderr)
    print("PERMITIDA — só não pode aparecer em string renderizada ao usuário.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Política: docs/reference/COPY_GUIDELINES.md §13", file=sys.stderr)
    print("Substituições: §13.2", file=sys.stderr)
    print("Exceção legítima: rebrand interno + nova ADR de licenciamento.", file=sys.stderr)


def _report_failures(failures: list[tuple[Path, list[tuple[int, str, str]]]]) -> None:
    _print_header()
    for path, hits in failures:
        _print_file_hits(path, hits)
    _print_footer()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="Arquivos a checar (default: argv).")
    parser.add_argument("--all", action="store_true", help="Scan completo da surface user-facing.")
    args = parser.parse_args(argv)

    candidates = collect_files(args.files, args.all)
    files_in_scope = [p for p in candidates if is_user_facing(relpath(p))]
    failures = [(p, hits) for p in files_in_scope if (hits := check_file(p))]

    if not failures:
        return 0
    _report_failures(failures)
    return 1


if __name__ == "__main__":
    sys.exit(main())
