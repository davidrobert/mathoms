#!/usr/bin/env python3
"""Valida que `lane.plan` aponta para um plano existente."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data = yaml.safe_load(text[4:end]) or {}
    return data if isinstance(data, dict) else {}


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _plan_ids() -> set[str]:
    ids: set[str] = set()
    for path in sorted((DOCS / "plan").glob("*/_README.md")):
        plan_id = _frontmatter(path).get("id")
        if isinstance(plan_id, str):
            ids.add(plan_id)
    return ids


def _lane_paths() -> list[Path]:
    return sorted((DOCS / "sprint").glob("*/lanes/*.md"))


def _broken_lane_refs(plan_ids: set[str]) -> list[tuple[Path, str]]:
    broken: list[tuple[Path, str]] = []
    for path in _lane_paths():
        plan = _frontmatter(path).get("plan")
        if plan is None:
            continue
        if not isinstance(plan, str) or plan not in plan_ids:
            broken.append((path, str(plan)))
    return broken


def main() -> int:
    plan_ids = _plan_ids()
    broken = _broken_lane_refs(plan_ids)
    for path, plan in broken:
        print(f"X {_rel(path)}")
        print(f"  lane.plan aponta para plano inexistente: {plan}")
    if broken:
        print(f"{len(broken)} lane.plan invalido(s).")
        return 1
    print(f"✓ lane.plan refs validas ({len(plan_ids)} planos canônicos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
