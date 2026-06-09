#!/usr/bin/env python3
"""Garante que a EXTRAÇÃO PURA não importa lógica de domínio (ADR-280); exit 1 = violação."""

# Critério de corte Extract|Transform: extração = função pura de *uma fonte → seus
# próprios registros* (não pode produzir campo dependente de outro registro, config
# de domínio do workspace, ou decisão metodológica). Irmão estático de
# `check_pipeline_boundaries` (AST de imports); trava o critério — o de-leak de regras
# que hoje vazam (`tipo_lancamento`, `numero_conta_norm`) é F2.
#
# Cobre por path (não rótulo no spec — minimiza blast radius nesta onda):
# `scripts/e2/**/*.py` (parsers + helpers) + `pipeline/stages/extract_*.py`.
# `consolidate_baseline` (E1.5c) é Transform — fora do glob por design (PODE importar
# domínio: lê cross-IRPF + dedup).
#
# Proíbe (conjunto MÍNIMO de F1, ampliável quando F2 mover regras): `category_template`,
# `*_dedup`/`*deduplicator*`, `config_store` (Protocol + impls). NÃO cobre
# `account_normalization`/`numero_conta_norm` nesta onda (alvo de F2).

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Raízes de extração pura (ADR-280). Globs relativos ao repo.
_EXTRACTION_GLOBS = ("scripts/e2/**/*.py", "pipeline/stages/extract_*.py")


def _is_forbidden(module: str) -> bool:
    """Casa por COMPONENTE do dotted-path (não substring crua: ``dedup_metrics`` não é dedup)."""
    parts = module.split(".")
    return any(
        "category_template" in p
        or "config_store" in p
        or p.endswith("_dedup")
        or "deduplicator" in p
        for p in parts
    )


def _imported_modules(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [node.module]
    return []


def _violations_in_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as e:
        return [f"{path}: parse error: {e}"]
    rel = path.relative_to(_REPO_ROOT)
    return [
        f"{rel}:{node.lineno}: forbidden domain import `{module}` (ADR-280)"
        for node in ast.walk(tree)
        for module in _imported_modules(node)
        if _is_forbidden(module)
    ]


def extraction_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in _EXTRACTION_GLOBS:
        files.update(p for p in _REPO_ROOT.glob(pattern) if "__pycache__" not in p.parts)
    return sorted(files)


def collect_violations() -> list[str]:
    errors: list[str] = []
    for path in extraction_files():
        errors.extend(_violations_in_file(path))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    errors = collect_violations()
    if args.verbose and not errors:
        print(
            f"OK: extração pura sem imports de domínio ({len(extraction_files())} arquivos)",
            file=sys.stderr,
        )
    for line in errors:
        print(line, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
