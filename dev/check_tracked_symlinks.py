#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev/check_tracked_symlinks.py — hook para pre-commit.

Falha (exit 1) se o índice do git tiver symlink cujo alvo é absoluto ou
escapa a raiz do repositório. Esse symlink resolve só na máquina de quem
commitou; em qualquer outro clone ele nasce quebrado.

Origem: b8460274 (PR #1258) rastreou `frontend-ops/node_modules` apontando
para `/Users/<user>/.../frontend-ops/node_modules` — o truque de worktree
(symlink das deps para o clone principal) escapou o `.gitignore`, que usava
`node_modules/` com barra final e por isso casava apenas diretórios.

Por que não bastam os hooks comunitários:

- `check-symlinks` acusa symlink **quebrado**. No momento do commit ofensor
  o alvo existia na máquina do dono — passaria limpo. Só acusa em CI, depois
  do estrago já estar em `main`.
- `destroyed-symlinks` cobre symlink virado arquivo regular (checkout sem
  suporte a symlink), classe ortogonal a esta.

Este gate olha o alvo, não a resolução — por isso pega no commit, na máquina
onde o alvo resolve. Alvo relativo dentro do repo (`AGENTS.md -> CLAUDE.md`)
é legítimo e passa.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from pathlib import Path

SYMLINK_MODE = "120000"

# `C:\...` / `C:/...` — alvo absoluto de Windows não é pego por startswith("/").
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


def _git(repo_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def tracked_symlinks(repo_root: Path) -> list[tuple[str, str]]:
    """Pares `(path, alvo)` de todo symlink no índice."""
    out: list[tuple[str, str]] = []
    for line in _git(repo_root, "ls-files", "-s").splitlines():
        meta, _, path = line.partition("\t")
        fields = meta.split()
        if len(fields) < 2 or fields[0] != SYMLINK_MODE:
            continue
        target = _git(repo_root, "cat-file", "-p", fields[1]).strip()
        out.append((path, target))
    return out


def violation_reason(path: str, target: str) -> str | None:
    """Razão da violação, ou None se o alvo é relativo e fica dentro do repo."""
    if target.startswith("/") or _WINDOWS_ABSOLUTE.match(target):
        return f"alvo absoluto {target!r} — resolve só na máquina que commitou"
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
    if resolved == ".." or resolved.startswith("../"):
        return f"alvo {target!r} escapa a raiz do repo (resolve em {resolved!r})"
    return None


def _report(violations: list[tuple[str, str]]) -> None:
    print("✗ pre-commit: symlink rastreado com alvo não-portável:", file=sys.stderr)
    for path, reason in violations:
        print(f"    {path} — {reason}", file=sys.stderr)
    print(
        "\nEsperado: alvo relativo que resolve dentro do repo (ex.: "
        "`AGENTS.md -> CLAUDE.md`).\n"
        "Se o symlink caiu aqui por engano (truque de worktree para deps):\n"
        "  - remova do índice: git rm --cached <path>\n"
        "  - confira o .gitignore — padrão com barra final casa só diretório,\n"
        "    e symlink homônimo escapa (use `node_modules`, não `node_modules/`)",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="raiz do repositório a inspecionar")
    args = parser.parse_args(argv)

    violations = [
        (path, reason)
        for path, target in tracked_symlinks(Path(args.repo))
        if (reason := violation_reason(path, target)) is not None
    ]
    if not violations:
        return 0
    _report(violations)
    return 1


if __name__ == "__main__":
    sys.exit(main())
