#!/usr/bin/env python3
"""Valida anchor links internos em docs/DECISIONS.md.

Implementa o algoritmo do GitHub Slugger usado pelo render do markdown
no GitHub para gerar âncoras a partir de headings. Cada referência
`[texto](#adr-...)` no arquivo é validada contra o conjunto de slugs
gerados a partir dos headings `## ADR-NNN — Título...`.

Uso:
    python3 dev/check_adr_anchors.py            # valida; exit 1 se broken
    python3 dev/check_adr_anchors.py --suggest  # sugere correções

Algoritmo do GitHub Slugger (validado empiricamente contra renders reais):
    1. lowercase
    2. remove caracteres não-alfanuméricos exceto `_`, `-` e ` `
       (preserva `_` em `for_tenant`; remove `:`, `/`, `.`, `,`, `(`, `)`,
       `≥`, `→`, etc.)
    3. espaços → hífen
    4. múltiplos hífens consecutivos preservados (em-dash ` — ` rodeado
       de espaços vira `--` no slug — convenção: o em-dash some, mas os
       2 espaços ao redor viram cada um um hífen).

Exit codes:
    0 — todos os anchors válidos
    1 — há broken anchors (lista impressa)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS = REPO_ROOT / "docs" / "DECISIONS.md"

HEADING_RE = re.compile(r"^## (ADR-[\w-]+ —.+)$", re.MULTILINE)
# Slugs incluem caracteres unicode latinos (ã, ç, é, ó, ú) gerados pelo
# GitHub Slugger — `\w` em re.UNICODE cobre, mas casamos explicitamente
# para evitar pegar caracteres não-slug.
ANCHOR_RE = re.compile(r"\[([^\]]+)\]\(#(adr-[\w\-]+)\)", re.UNICODE)


def github_slug(heading_text: str) -> str:
    """Converte um heading markdown no slug que o GitHub gera.

    Regras (validadas contra render real do GitHub):
    - lowercase
    - remove qualquer char que não seja [a-z0-9_- ] após lowercase
    - espaços viram hífens
    """
    s = heading_text.lower()
    s = re.sub(r"[^\w\- ]+", "", s, flags=re.UNICODE)
    s = s.replace(" ", "-")
    return s


def collect_headings(content: str) -> dict[str, str]:
    """Mapeia título-completo→slug-canônico para cada ADR no arquivo."""
    out: dict[str, str] = {}
    for match in HEADING_RE.finditer(content):
        title = match.group(1).strip()
        out[title] = github_slug(title)
    return out


def collect_anchor_refs(content: str) -> list[tuple[int, str, str]]:
    """Retorna [(linha, texto_link, slug_citado)] para cada `[X](#adr-...)`.

    Ignora linhas dentro de blocos de código (cercados por ```).
    """
    refs: list[tuple[int, str, str]] = []
    in_code_block = False
    for line_no, line in enumerate(content.splitlines(), start=1):
        # Aceita fence em código normal (```), em blockquote (> ```) e
        # com indentação variável.
        stripped = line.lstrip("> \t")
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        for match in ANCHOR_RE.finditer(line):
            refs.append((line_no, match.group(1), match.group(2)))
    return refs


def find_closest(slug: str, valid_slugs: set[str]) -> str | None:
    """Heurística: tenta achar o slug válido mais parecido com o quebrado.

    Estratégia: se o ID `adr-NNN` casa, retorna o slug válido com mesmo
    prefixo numérico.
    """
    m = re.match(r"^(adr-\d{3}(?:-[a-z]+)?)--?", slug)
    if not m:
        return None
    adr_id = m.group(1)
    candidates = [s for s in valid_slugs if s.startswith(adr_id + "--")]
    return candidates[0] if len(candidates) == 1 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Imprimir correções sugeridas (sed-friendly)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DECISIONS,
        help="Caminho do markdown (default: docs/DECISIONS.md)",
    )
    args = parser.parse_args()

    content = args.file.read_text(encoding="utf-8")
    headings = collect_headings(content)
    valid_slugs = set(headings.values())
    refs = collect_anchor_refs(content)

    broken: list[tuple[int, str, str, str | None]] = []
    for line_no, text, cited in refs:
        if cited not in valid_slugs:
            suggestion = find_closest(cited, valid_slugs)
            broken.append((line_no, text, cited, suggestion))

    print(f"docs/DECISIONS.md — {len(headings)} headings, {len(refs)} anchor refs")

    if not broken:
        print("✓ todos os anchor links válidos")
        return 0

    print(f"✗ {len(broken)} anchor link(s) broken:\n")
    for line_no, text, cited, suggestion in broken:
        print(f"  L{line_no}: [{text}](#{cited})")
        if suggestion:
            print(f"    → sugerido: #{suggestion}")
        else:
            print("    → (sem sugestão automática — verificar manualmente)")
        if args.suggest and suggestion:
            print(f"    sed: s|#{cited}|#{suggestion}|g")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
