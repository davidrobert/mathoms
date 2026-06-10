#!/usr/bin/env python3
"""Gate do lineage_registry (ADR-281 B2): cada ``rule_ref`` resolve por import real + ADR existe.

Para cada entrada de ``pipeline.domain.lineage_registry.LINEAGE_RULE_REFS``,
resolve ``module:qualname`` via importlib + getattr e verifica que
``docs/adr/<nnn>-*.md`` do campo ``adr`` existe. Exit 1 com valor ofensor —
é o que torna o bridge nó→código refactor-safe (rename sem atualizar o
dict quebra no pre-commit).
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

_ADR_RE = re.compile(r"^ADR-(\d+)$")
_SENTINEL = object()


def check_ref(ref: str) -> str | None:
    """None se ``module:qualname`` resolve por import real; senão a violação."""
    module_name, sep, qualname = ref.partition(":")
    if not sep or not module_name or not qualname:
        return f"ref malformado (esperado 'module:qualname'), got {ref!r}"
    try:
        target = importlib.import_module(module_name)
    except ImportError as exc:
        return f"módulo não importável em ref {ref!r}: {exc}"
    for attr in qualname.split("."):
        target = getattr(target, attr, _SENTINEL)
        if target is _SENTINEL:
            return f"qualname não resolve em ref {ref!r}: atributo {attr!r} inexistente"
    return None


def check_adr(adr: str) -> str | None:
    """None se ``docs/adr/<nnn>-*.md`` existe; senão a violação."""
    match = _ADR_RE.match(adr)
    if match is None:
        return f"adr deve casar 'ADR-NNN', got {adr!r}"
    pattern = f"{int(match.group(1)):03d}-*.md"
    if not list((_REPO / "docs" / "adr").glob(pattern)):
        return f"ADR inexistente em docs/adr/ (esperado {pattern}), got {adr!r}"
    return None


def check_registry(registry: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for rule_id, entry in sorted(registry.items()):
        problems = [check_ref(entry.get("ref", "")), check_adr(entry.get("adr", ""))]
        errors.extend(f"{rule_id}: {p}" for p in problems if p is not None)
    return errors


def main(registry: dict[str, dict[str, str]] | None = None) -> int:
    if registry is None:
        from pipeline.domain.lineage_registry import LINEAGE_RULE_REFS

        registry = LINEAGE_RULE_REFS
    errors = check_registry(registry)
    for error in errors:
        print(f"check_lineage_refs: {error}", file=sys.stderr)
    if not errors:
        print(f"check_lineage_refs: OK ({len(registry)} rule_refs resolvem)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
