#!/usr/bin/env python3
"""Hook pre-commit: bloqueia adições novas de `residencia_principal_keyword` (ADR-215 P6)."""
# Allowlist explícita das fontes legadas que mantêm leitura como fallback
# durante deprecation (1 sprint pós-cutover). Qualquer adição em arquivo
# fora dessa lista aborta o commit. Lista vive em `_ALLOWED_FILES` abaixo.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_NEEDLE = b"residencia_principal_keyword"

_ALLOWED_FILES = frozenset(
    {
        # Pós-sunset (ADR-215 §1 Decidido completo): apenas o gate em si +
        # script de migration histórico + ADR/plan/changelog (docs anchoring)
        # + MOCs auto-gerados (citam title da ADR-215) ainda podem citar a
        # needle. Nenhum código runtime persiste keyword.
        "dev/check_residencia_keyword.py",
        "dev/migrate_residencia_keyword_to_override.py",
        "docs/adr/215-classificacao-imoveis-override-db-first.md",
        "docs/plan/RESIDENCIA_E_USO/_README.md",
        "docs/CHANGELOG.md",
        "docs/_MOC/_generated/INDEX.md",
        "docs/_MOC/_generated/ADR_INDEX.md",
    }
)


def _staged_diff_lines() -> list[bytes]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "-U0", "-M", "--no-color"],
        capture_output=True,
        check=False,
    )
    return proc.stdout.splitlines() if proc.returncode == 0 else []


def _is_added_needle_line(line: bytes) -> bool:
    return line.startswith(b"+") and not line.startswith(b"+++") and _NEEDLE in line


def _files_with_added_needle() -> set[str]:
    """Paths (lado `b/`) cujo diff staged adiciona linha com a needle.

    Diff único com `-M`: pathspec por arquivo quebraria o pareamento de
    rename e faria `git mv` reportar o arquivo inteiro como adição (F9.4).
    """
    files: set[str] = set()
    current: str | None = None
    for line in _staged_diff_lines():
        if line.startswith(b"+++ b/"):
            current = line[6:].decode("utf-8", errors="replace")
            continue
        if current is not None and _is_added_needle_line(line):
            files.add(current)
    return files


def main(argv: list[str]) -> int:
    needle_files = _files_with_added_needle()
    violations: list[str] = []
    for raw in argv:
        path = raw.lstrip("./")
        if path in _ALLOWED_FILES:
            continue
        if not path.endswith((".py", ".ts", ".tsx", ".js", ".json", ".md", ".yaml")):
            continue
        if path in needle_files:
            violations.append(path)

    if violations:
        sys.stderr.write(
            "ERRO ADR-215 P6: `residencia_principal_keyword` é dead code "
            "(override DB substituiu). Adições novas bloqueadas em:\n"
        )
        for v in violations:
            sys.stderr.write(f"  - {v}\n")
        sys.stderr.write(
            "\nLeitura legada permanece como fallback nos arquivos do pipeline "
            "até deprecation completa. Para classificação nova use o endpoint\n"
            "  `PUT /workspaces/{ws}/properties/{id}/classification`\n"
            "ou o use case `set_property_classification`.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
