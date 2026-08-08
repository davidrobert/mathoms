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
       - `COPY_YAML_FILES` (`config/report_layout.yaml`) — copy que chega à
         UI via codegen (ADR-076). Parse + varredura de valores em vez de
         line-scan; internals e rationale em `dev/_sigilo_copy_yaml.py`.
         `frontend/src/generated/` NÃO entra: derivado se gateia na fonte.
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

**Superset público (A34.l5 · ADR-319):** além da surface user-facing acima,
o flip público ([[PLAN-public-release]]) exige zero atribuição nominal em
todo path que sobrevive ao repo público — `docs/**`, `config/prompts/**`,
`README*`, migrations de seed. Nesses paths a regra é DIFERENTE da §13.4:

  - match case-INSENSITIVE dos termos-núcleo (perini|cerbasi|auvp|
    raul sena|viver de renda) — "atribuição interna" deixa de existir
    quando o repo é público;
  - SEM strip de comentários — docstring/comment também é publicado;
  - hits legados (~200 arquivos) vivem no baseline burn-down
    `dev/sigilo_terms_baseline.json` até a A34.l12 / ADR-314 redigir ou
    mover o conteúdo. Hit NOVO fora do baseline → exit 1.
  - allowlist permanente mínima: apenas os docs que DEFINEM a política
    (ADR-183, COPY_GUIDELINES §13) — citam os termos por necessidade.

Uso:
  python3 dev/check_sigilo_terms.py [<file> ...]   # checa arquivos passados
  python3 dev/check_sigilo_terms.py --all          # scan completo do repo
  python3 dev/check_sigilo_terms.py --all --no-baseline   # prova G2 (estrito)
  python3 dev/check_sigilo_terms.py --all --update-baseline

Retorna exit 0 se zero hits fora de allowlist/baseline; exit 1 caso contrário.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev._sigilo_copy_yaml import (  # noqa: E402  (import depois de sys.path)
    COPY_YAML_FILES,
    is_copy_yaml,
)
from dev._sigilo_copy_yaml import (
    find_hits as _yaml_copy_hits,
)

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
# Superset público (A34.l5 · ADR-319) — paths que sobrevivem ao flip.
# ---------------------------------------------------------------------------
FORBIDDEN_PUBLIC_RE = re.compile(r"(?i)\b(perini|cerbasi|auvp|raul\s+sena|viver\s+de\s+renda)\b")

PUBLIC_SUPERSET_RULES = (
    ("docs/", (".md",)),
    ("config/prompts/", (".yaml", ".yml")),
    # Migrations de seed inserem dados de exemplo que viram DB de produção
    # E texto público no repo.
    ("backend/alembic/versions/", (".py",)),
)

# Allowlist PERMANENTE mínima — somente docs que definem a política de
# sigilo e portanto citam os termos por necessidade operacional. Qualquer
# entrada nova exige justificativa inline (ADR-319).
PUBLIC_ALLOWLIST = frozenset(
    {
        # Define os pilares narrativos + vocabulário substituto canônico.
        "docs/adr/183-landing-positioning-pillars-2026.md",
        # §13 é a política de sigilo em si (termos proibidos + substituições).
        "docs/reference/COPY_GUIDELINES.md",
    }
)

# Baseline burn-down: hits legados por path, pendentes de redação/split na
# A34.l12 (ADR-314). NUNCA adicionar entrada sem lane de saneamento.
PUBLIC_BASELINE_PATH = REPO_ROOT / "dev" / "sigilo_terms_baseline.json"

# Artefatos DERIVADOS (auto-gerados por dev/build_doc_index.py) — nunca
# editados à mão. Reagregam texto das notas-fonte, então gatear aqui é
# redundante (a fonte já é coberta pelo superset) e frágil: cada regeneração
# que toca lanes muda o conteúdo, reintroduzindo "hits" de fonte já
# baselineada e quebrando o gate em PR sem relação. A neutralização em W1
# propaga via regen. Excluídos do scan de sigilo (A34.l5).
_DERIVED_PREFIXES = ("docs/_MOC/_generated/",)

# Dirs ignorados na varredura de README* repo-wide.
_README_EXCLUDED_PARTS = {
    "node_modules",
    ".git",
    ".venv",
    "_archive",
    "_scratch",
    ".claude",
    ".next",
    "storage",
    "__pycache__",
}


def is_public_superset(rel_path: str) -> bool:
    """True se rel_path faz parte do superset público (A34.l5)."""
    if any(rel_path.startswith(p) for p in _DERIVED_PREFIXES):
        return False
    basename = rel_path.rsplit("/", 1)[-1]
    if basename.startswith("README"):
        return not any(part in _README_EXCLUDED_PARTS for part in rel_path.split("/"))
    for prefix, suffixes in PUBLIC_SUPERSET_RULES:
        if rel_path.startswith(prefix) and rel_path.endswith(suffixes):
            return True
    return False


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


def check_file_yaml_copy(path: Path) -> list[tuple[int, str, str]]:
    """Hits §13.1 nos valores string de YAML de copy (config → codegen → UI)."""
    return _dedupe(_yaml_copy_hits(path, FORBIDDEN_RE))


def check_file_public(path: Path) -> list[tuple[int, str, str]]:
    """Hits do superset público — case-insensitive, sem strip de comentários (repo público não tem "atribuição interna"; A34.l5 · ADR-319)."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    hits: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(content.splitlines(), 1):
        for match in FORBIDDEN_PUBLIC_RE.finditer(line):
            hits.append((line_no, match.group(1), line.rstrip()))
    return _dedupe(hits)


def _load_public_baseline() -> set[str]:
    if not PUBLIC_BASELINE_PATH.exists():
        return set()
    data = json.loads(PUBLIC_BASELINE_PATH.read_text(encoding="utf-8"))
    return set(data.get("paths", []))


def _write_public_baseline(paths: set[str]) -> None:
    payload = {
        "_comment": (
            "Baseline burn-down do gate de sigilo no superset público "
            "(A34.l5, ADR-319). Paths legados com atribuição nominal, "
            "pendentes de redação/split na A34.l12 (ADR-314). Hit fora "
            "do baseline é gate; entrada nova exige lane de saneamento."
        ),
        "paths": sorted(paths),
    }
    PUBLIC_BASELINE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


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


def _collect_all_public_superset() -> list[Path]:
    """rglob do superset público: PUBLIC_SUPERSET_RULES + README* repo-wide."""
    candidates: list[Path] = []
    for prefix, suffixes in PUBLIC_SUPERSET_RULES:
        base = REPO_ROOT / prefix
        if not base.exists():
            continue
        for suffix in suffixes:
            candidates.extend(base.rglob(f"*{suffix}"))
    candidates.extend(
        p
        for p in REPO_ROOT.rglob("README*")
        if not any(part in _README_EXCLUDED_PARTS for part in p.parts)
    )
    return sorted({p for p in candidates if p.is_file()})


def collect_files(args_files: list[str], scan_all: bool) -> list[Path]:
    """Resolve lista de arquivos a checar."""
    if scan_all:
        copy_yaml = [p for rel in sorted(COPY_YAML_FILES) if (p := REPO_ROOT / rel).is_file()]
        return sorted({*_collect_all_user_facing(), *_collect_all_public_superset(), *copy_yaml})
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


def _public_failures(
    candidates: list[Path], baseline: set[str]
) -> tuple[list[tuple[Path, list[tuple[int, str, str]]]], int, set[str]]:
    """(failures, n_baselined, all_hit_paths) do superset público."""
    failures: list[tuple[Path, list[tuple[int, str, str]]]] = []
    baselined = 0
    all_hit_paths: set[str] = set()
    for p in candidates:
        rel = relpath(p)
        if not is_public_superset(rel) or rel in PUBLIC_ALLOWLIST:
            continue
        hits = check_file_public(p)
        if not hits:
            continue
        all_hit_paths.add(rel)
        if rel in baseline:
            baselined += 1
        else:
            failures.append((p, hits))
    return failures, baselined, all_hit_paths


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="Arquivos a checar (default: argv).")
    parser.add_argument("--all", action="store_true", help="Scan completo da surface user-facing.")
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Modo estrito (prova G2): ignora o baseline do superset público.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Regenera dev/sigilo_terms_baseline.json (apenas em lane de saneamento).",
    )
    return parser.parse_args(argv)


def _user_facing_failures(candidates: list[Path]) -> list[tuple[Path, list[tuple[int, str, str]]]]:
    """Hits na surface user-facing legada (§13.4: case-sensitive + strip de comentários)."""
    files = [p for p in candidates if is_user_facing(relpath(p))]
    return [(p, hits) for p in files if (hits := check_file(p))]


def _copy_yaml_failures(candidates: list[Path]) -> list[tuple[Path, list[tuple[int, str, str]]]]:
    """Hits em valores de YAML de copy (config → codegen → UI)."""
    files = [p for p in candidates if is_copy_yaml(relpath(p))]
    return [(p, hits) for p in files if (hits := check_file_yaml_copy(p))]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    candidates = collect_files(args.files, args.all or args.update_baseline)
    baseline = set() if args.no_baseline else _load_public_baseline()
    public_failures, baselined, all_hit_paths = _public_failures(candidates, baseline)

    if args.update_baseline:
        _write_public_baseline(all_hit_paths)
        print(f"Baseline de sigilo regenerado: {len(all_hit_paths)} paths.")
        return 0

    failures = _user_facing_failures(candidates) + _copy_yaml_failures(candidates) + public_failures
    if baselined:
        print(f"ℹ {baselined} path(s) legados no baseline sigilo (A34.l12).", file=sys.stderr)
    if not failures:
        return 0
    _report_failures(failures)
    return 1


if __name__ == "__main__":
    sys.exit(main())
