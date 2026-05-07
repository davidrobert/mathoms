#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev/check_forbidden_paths.py — hook para pre-commit.

Recebe paths via argv (comportamento padrão do pre-commit) e falha (exit 1)
se qualquer um estiver em diretório proibido, for arquivo proibido por nome
ou tiver sufixo proibido.

Mantém em sincronia com `dev/commit.py`: a intenção é que pre-commit rode
esta mesma validação em CI, git hooks locais e via dev/commit.py — defense
in depth.

Nota: `storage/` cobre uploads multi-tenant; `data/`/`inbox/` cobrem o pipeline
CLI na raiz do repo — ver `dev/README.md`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Alinhado com dev/commit.py — mudar lá mudar aqui.
FORBIDDEN_DIRS = (
    "storage/",
    "data/",
    "inbox/",
    "inbox_processed/",
    "_scratch/",
    # A7.6 (ADR-143): rules-as-code dissolveu docs/methodology/. Bloquear
    # recriação acidental — regras universais vivem em docstrings + ADRs;
    # dados cliente em DB ou <workspace>/notes/ (gitignored).
    "docs/methodology/",
)

FORBIDDEN_FILES = (
    "mathoms.db",
    "config/passwords.txt",
    # F7F-Local (ADR-116): credenciais de operadores internos nunca vão
    # para o git. Apenas `config/internal_operators.example.yaml` é commitável.
    "config/internal_operators.yaml",
    # A7.2a (ADR-136): caderno editorial do cliente migrou para o aggregate
    # `Decision`. Re-introduzir o arquivo violaria a política PII (valores BRL
    # reais em git).
    "config/decisions.md",
    # A7.4: docs metodológicas movidas de config/ → docs/methodology/. Bloquear
    # ressurgimento dos paths antigos (regressão acidental ou rebase com conflito).
    # A7.6 (ADR-143): docs/methodology/ também dissolvido (ver FORBIDDEN_DIRS).
    "config/definitions.md",
    "config/regras_composicao_patrimonial.md",
    "config/source_hierarchy.md",
    "config/milhas.md",
    # A7.5 (ADR-134/135/137): cleanup final do plano CONFIG_CUTOVER. Os 5
    # arquivos abaixo migraram para DB (ConfigStore) ou tabelas globais
    # versionadas. Re-introduzi-los reabre dual-source-of-truth.
    # ``config/report_layout.yaml`` permanece em ``config/`` por ser source-of-
    # truth do codegen ``dev/codegen_report_layout.py`` + default global do
    # blob no API config. Migração para fora de ``config/`` é débito A8.
    "config/categorization.json",
    "config/family_members.json",
    "config/institutions.json",
    "config/parametros_fiscais.json",
    "config/taxas.json",
    # A10.8 (ADR-181): último JSON do cluster `config/*.json` migrado.
    # ADR-180 (Sprint A10.6) eliminou materialização runtime; arquivo
    # arquivado em `_archive/.../goals.json` deletado em A10.8 e
    # substituído por `goals.json.MIGRATED.md`. Recriação no path
    # original violaria o cutover — ADR-077 checkbox fechado.
    "config/goals.json",
)

# Basenames bloqueados em qualquer diretório (regressão: backend/.env vazou
# porque o match era exato; .env no root era pego, subdirs passavam).
FORBIDDEN_BASENAMES = (
    ".env",
    ".env.test",
)

FORBIDDEN_SUFFIXES = (
    ".db",
    ".sqlite",
    ".sqlite3",
)


def _staged_deletion_paths(repo_root: Path) -> set[str]:
    """Paths com delete staged (`git diff --cached`) — remover `.env` do repo é OK."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--cached", "--name-status"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode != 0 or not proc.stdout:
        return set()
    out: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if status == "D":
            out.add(parts[1])
    return out


def check(path: str, *, staged_deletions: set[str] | None = None) -> str | None:
    """Retorna a razão da violação, ou None se passou."""
    is_deletion = staged_deletions is not None and path in staged_deletions
    for forbidden in FORBIDDEN_DIRS:
        if path.startswith(forbidden):
            # Permite deletar (cleanup A7.6, ressincronização .gitignore, etc.).
            return None if is_deletion else f"diretório proibido: {forbidden}"
    basename = path.rsplit("/", 1)[-1]
    if basename in FORBIDDEN_BASENAMES:
        return None if is_deletion else f"arquivo proibido: {basename} (em {path})"
    if path in FORBIDDEN_FILES:
        return None if is_deletion else f"arquivo proibido: {path}"
    for suffix in FORBIDDEN_SUFFIXES:
        if path.endswith(suffix):
            return f"sufixo proibido: {suffix}"
    return None


def main() -> int:
    repo_root = Path.cwd()
    staged_del = _staged_deletion_paths(repo_root)
    violations: list[tuple[str, str]] = []
    for path in sys.argv[1:]:
        reason = check(path, staged_deletions=staged_del)
        if reason:
            violations.append((path, reason))

    if not violations:
        return 0

    print("✗ pre-commit: paths proibidos detectados:", file=sys.stderr)
    for path, reason in violations:
        print(f"    {path} — {reason}", file=sys.stderr)
    print(
        "\nEsses paths nunca devem ir pro git. Se caíram aqui por engano:\n"
        "  - verifique o .gitignore\n"
        "  - remova do staging: git restore --staged <path>\n"
        "  - em último caso, contorne com --no-verify (NÃO recomendado)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
