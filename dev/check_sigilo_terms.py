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

  1. Restringe surface a:
       - `frontend/src/app/` + `frontend/src/components/` (UI cliente)
       - `docs/_marketing/` (drafts de copy comercial — landing, e-mail,
         pitch, comparativo competitivo). Suffix `.md` é user-facing
         **somente** sob esse prefixo; o resto de `docs/` continua interno
         (ADRs, planos, runbooks atribuem livremente — §13.4).
  2. Exclui paths internal-only conhecidos (types, api contract, generated,
     dev playground, variant-key components, barrel exports, `_README.md`
     de `docs/_marketing/` cuja função é descritiva interna).
  3. Strip comentários antes do grep — atribuição em docstring permanece OK:
       - JS/TS: block `/* */` + line `//`.
       - Markdown: HTML `<!-- … -->` (block) + fenced code blocks
         (``` … ```). Inline code `` `…` `` é preservado (geralmente
         identificador técnico, não copy renderizada).
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
# Pares (prefix, suffix) que descrevem a surface user-facing. Cada par é
# enforçado em conjunto: arquivo é user-facing se algum par casa.
USER_FACING_RULES = (
    ("frontend/src/app/", (".tsx", ".ts")),
    ("frontend/src/components/", (".tsx", ".ts")),
    ("docs/_marketing/", (".md",)),
)

# Compat: união planar dos prefixes/suffixes para callers que ainda esperam
# tuplas separadas (rglob e similares).
USER_FACING_PREFIXES = tuple(prefix for prefix, _ in USER_FACING_RULES)
USER_FACING_SUFFIXES = tuple(sorted({s for _, suffixes in USER_FACING_RULES for s in suffixes}))

# Exclusões — paths internal-only por convenção (§13.4 atribuição PERMITIDA).
EXCLUDED_PREFIXES = ("frontend/src/app/(app)/reports/_dev/",)
EXCLUDED_FILES = frozenset(
    {
        # Variant key "cerbasi" como literal técnico, não user-facing.
        "frontend/src/components/report/ui/NotasInsightsGrid.tsx",
        # Barrel exports — re-exporta nomes de componentes internos.
        "frontend/src/components/report/cards/index.ts",
        # README descritivo interno do diretório de drafts marketing.
        "docs/_marketing/_README.md",
    }
)

# ---------------------------------------------------------------------------
# Comment stripping — atribuição em docstring é permitida (§13.4).
# Ordem importa: block primeiro, depois line.
# ---------------------------------------------------------------------------
BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/", re.MULTILINE)
LINE_COMMENT_RE = re.compile(r"//[^\n]*", re.MULTILINE)
HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->", re.MULTILINE)
FENCED_CODE_RE = re.compile(r"^```[\s\S]*?^```", re.MULTILINE)


def is_user_facing(rel_path: str) -> bool:
    """True se rel_path casa algum (prefix, suffix) de USER_FACING_RULES e
    não está excluído."""
    if any(rel_path.startswith(p) for p in EXCLUDED_PREFIXES):
        return False
    if rel_path in EXCLUDED_FILES:
        return False
    for prefix, suffixes in USER_FACING_RULES:
        if rel_path.startswith(prefix) and rel_path.endswith(suffixes):
            return True
    return False


def _is_markdown(rel_path: str) -> bool:
    return rel_path.endswith(".md")


def _block_to_blank_lines(match: re.Match[str]) -> str:
    """Substitui block por quebras de linha — preserva line numbers nos hits."""
    return "\n" * match.group(0).count("\n")


def strip_comments(content: str, *, markdown: bool = False) -> str:
    """Remove comentários antes do grep.

    JS/TS: block `/* */` + line `//`.
    Markdown: HTML `<!-- ... -->` + fenced code blocks (``` ... ```).
    Inline code `` `…` `` é preservado intencionalmente — geralmente
    contém identificador técnico, não copy renderizada.

    Substitui blocos por quebras de linha para que line numbers nos hits
    permaneçam corretos.
    """
    if markdown:
        no_html = HTML_COMMENT_RE.sub(_block_to_blank_lines, content)
        return FENCED_CODE_RE.sub(_block_to_blank_lines, no_html)
    no_block = BLOCK_COMMENT_RE.sub(_block_to_blank_lines, content)
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
    stripped = strip_comments(content, markdown=_is_markdown(relpath(path)))
    raw_hits = _scan_for_hits(stripped.splitlines(), content.splitlines())
    return _dedupe(raw_hits)


def _collect_all_user_facing() -> list[Path]:
    """rglob em cada (prefix, suffix) de USER_FACING_RULES."""
    candidates: list[Path] = []
    for prefix, suffixes in USER_FACING_RULES:
        base = REPO_ROOT / prefix
        if not base.exists():
            continue
        for suffix in suffixes:
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
