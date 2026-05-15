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
        "pipeline/domain/services/patrimonio_calculator.py",
        "pipeline/domain/services/patrimonio_types.py",
        "pipeline/domain/services/e5_analyzer_adapter.py",
        "pipeline/domain/services/member_analyzer.py",
        "pipeline/domain/services/investimentos_classes_analyzer.py",
        "pipeline/domain/services/top_ativos_analyzer.py",
        "pipeline/domain/services/instituicoes_por_membro_analyzer.py",
        "scripts/e5_analyze.py",
        "dev/check_residencia_keyword.py",
        "dev/migrate_residencia_keyword_to_override.py",
        "docs/adr/215-classificacao-imoveis-override-db-first.md",
        "docs/plan/RESIDENCIA_E_USO/_README.md",
        "docs/reference/DB_SCHEMA_REFERENCE.md",
        "docs/CHANGELOG.md",
    }
)


def _added_lines_contain_needle(path: str) -> bool:
    """True se o diff contém adição (linha começando com `+`) com a needle."""
    proc = subprocess.run(
        ["git", "diff", "--cached", "-U0", "--", path],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return False
    for line in proc.stdout.splitlines():
        if line.startswith(b"+") and not line.startswith(b"+++") and _NEEDLE in line:
            return True
    return False


def main(argv: list[str]) -> int:
    violations: list[str] = []
    for raw in argv:
        path = raw.lstrip("./")
        if path in _ALLOWED_FILES:
            continue
        if not path.endswith((".py", ".ts", ".tsx", ".js", ".json", ".md", ".yaml")):
            continue
        if _added_lines_contain_needle(path):
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
