#!/usr/bin/env python3
"""Bloqueia NOVO consumidor de campo de extração em de-leak (F2 · ADR-280); exit 1 = reader novo."""

# `tipo_lancamento` e `numero_conta_norm` são campos que a F2 remove do output
# da extração (dead-downstream, discovery A24.l1). O strip+rerun com zero delta
# foi prova one-shot; ESTE gate é a guarda contínua: se alguém reintroduzir
# leitura dos campos em `pipeline/**` ou `backend/**`, falha aqui antes do
# campo voltar a ser load-bearing. Allowlist NOMINAL (path → motivo) para os
# toques conhecidos da janela de migração; scan textual barato (O(grep)).

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_LEAK_FIELDS = ("tipo_lancamento", "numero_conta_norm")
_SCAN_GLOBS = ("pipeline/**/*.py", "backend/**/*.py")

# (path relativo, campo) → motivo do toque permitido durante a janela F2.
_ALLOWLIST: dict[tuple[str, str], str] = {
    (
        "pipeline/domain/models/document.py",
        "numero_conta_norm",
    ): "fallback re-normalizador da janela ADR-226 (re-deriva, não depende do E2)",
    (
        "pipeline/domain/services/e2_natural_key.py",
        "tipo_lancamento",
    ): "comentário documentando que K4 NÃO usa o campo",
}


def _scan_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in _SCAN_GLOBS:
        files.update(
            p
            for p in _REPO_ROOT.glob(pattern)
            if "__pycache__" not in p.parts and "tests" not in p.parts
        )
    return sorted(files)


def _violations_in_file(path: Path) -> list[str]:
    rel = str(path.relative_to(_REPO_ROOT))
    text = path.read_text(encoding="utf-8")
    return [
        f"{rel}:{i}: consumidor de campo em de-leak `{field}` (F2/ADR-280) — "
        "não reintroduza; re-derive na Transform"
        for field in _LEAK_FIELDS
        if (rel, field) not in _ALLOWLIST
        for i, line in enumerate(text.splitlines(), 1)
        if field in line
    ]


def collect_violations(files: list[Path] | None = None) -> list[str]:
    errors: list[str] = []
    for path in files if files is not None else _scan_files():
        errors.extend(_violations_in_file(path))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    errors = collect_violations()
    if args.verbose and not errors:
        print(f"OK: nenhum consumidor novo de {_LEAK_FIELDS}", file=sys.stderr)
    for line in errors:
        print(line, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
