#!/usr/bin/env python3
"""Valida FKs do frontmatter: `lane.plan` e arestas wikilink resolvem (A40.l23)."""
# Sucessor de check_lane_plan_refs.py, que só cobria `lane.plan`.
# `check_doc_links.py` NUNCA vê o frontmatter — `_strip_frontmatter_preserving_lines`
# o apaga antes de extrair wikilinks —, então `depends_on: "[[id-inexistente]]"`
# passava nos cinco gates de doc. Resolvemos pelo MESMO index do check_doc_links
# (id + aliases) para que aresta de frontmatter e wikilink de corpo tenham uma
# regra só. Os campos de EDGE_FIELDS foram medidos na vault viva, não presumidos.

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import check_doc_links
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"

EDGE_FIELDS = (
    "depends_on",
    "parallel_with",
    "prompt",
    "adrs",
    "adrs_canonical",
    "supersedes",
    "superseded_by",
)

# `[[Alvo]]`, `[[Alvo|apelido]]`, `[[Alvo#anchor]]` — captura só o alvo.
WIKILINK_TARGET_RE = re.compile(r"^\[\[([^\]|#]+)")


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        data = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _plan_ids(docs: Path) -> set[str]:
    ids: set[str] = set()
    for path in sorted((docs / "plan").glob("*/_README.md")):
        plan_id = _frontmatter(path).get("id")
        if isinstance(plan_id, str):
            ids.add(plan_id)
    return ids


def _lane_paths(docs: Path) -> list[Path]:
    return sorted((docs / "sprint").glob("*/lanes/*.md"))


def broken_plan_refs(docs: Path) -> list[tuple[Path, str]]:
    """Lanes cujo `plan:` não aponta para um `docs/plan/*/_README.md` existente."""
    plan_ids = _plan_ids(docs)
    broken: list[tuple[Path, str]] = []
    for path in _lane_paths(docs):
        plan = _frontmatter(path).get("plan")
        if plan is None:
            continue
        if not isinstance(plan, str) or plan not in plan_ids:
            broken.append((path, str(plan)))
    return broken


# Valor não-wikilink é violação de schema — escopo do validate_frontmatter,
# não deste gate; por isso é filtrado em silêncio em vez de reportado.
def _field_targets(value: Any) -> list[str]:
    """Alvos de wikilink num valor de campo de aresta (escalar ou lista)."""
    items = value if isinstance(value, list) else [value]
    matches = (WIKILINK_TARGET_RE.match(i.strip()) for i in items if isinstance(i, str))
    return [m.group(1).strip() for m in matches if m]


def _edge_targets(fm: dict[str, Any]) -> list[tuple[str, str]]:
    """Pares (campo, alvo) de todo wikilink em campo de aresta do frontmatter."""
    return [
        (field, target)
        for field in EDGE_FIELDS
        if fm.get(field) is not None
        for target in _field_targets(fm[field])
    ]


def broken_edges(docs: Path) -> list[tuple[Path, str, str]]:
    """Arestas de frontmatter cujo alvo não é id nem alias de nota existente."""
    index, _ = check_doc_links.build_id_index(check_doc_links.collect_notes(docs))
    return [
        (path, field, target)
        for path in sorted(docs.rglob("*.md"))
        for field, target in _edge_targets(_frontmatter(path))
        if target not in index
    ]


def _report(plan_refs: list[tuple[Path, str]], edges: list[tuple[Path, str, str]]) -> None:
    for path, plan in plan_refs:
        print(f"X {_rel(path)}")
        print(f"  lane.plan aponta para plano inexistente: {plan}")
    for path, field, target in edges:
        print(f"X {_rel(path)}")
        print(f"  {field} aponta para nota inexistente: [[{target}]]")


def main(argv: list[str] | None = None) -> int:
    docs = Path(argv[0]).resolve() if argv else DOCS
    plan_refs = broken_plan_refs(docs)
    edges = broken_edges(docs)
    _report(plan_refs, edges)
    if plan_refs or edges:
        print(
            f"\n{len(plan_refs)} lane.plan inválido(s) e {len(edges)} aresta(s) órfã(s).\n"
            "Aresta de frontmatter é invisível ao check_doc_links (ele apaga o "
            "frontmatter antes de extrair wikilinks) — corrija o alvo ou remova a aresta."
        )
        return 1
    print(f"✓ FKs de frontmatter resolvem ({len(_plan_ids(docs))} planos canônicos).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
