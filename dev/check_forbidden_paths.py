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
    # A34.l6 (ADR-319): `_archive/` concentrava PII histórica (PDFs bancários
    # reais) e foi deletado na A34.l7; `archive/` bloqueia a variante de
    # recriação na raiz. `docs/archive/` NÃO casa (paths são raiz-relativos)
    # e permanece livre.
    "_archive/",
    "archive/",
)

# A34.l7: o grace temporário da A34.l6 (arquivos legados tracked em
# `_archive/`) saiu junto com a deleção do diretório — bloqueio agora é
# incondicional; a tupla permanece só pela mensagem de erro dedicada.
ARCHIVE_MESSAGE_DIRS = (
    "_archive/",
    "archive/",
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


def _staged_status_by_path(repo_root: Path) -> dict[str, str]:
    """Status staged por path (`git diff --cached --name-status`).

    Valores: primeira letra do status git ("A", "M", "D", "R", "C"…). Para
    rename/copy (`R100\told\tnovo`), o path registrado é o destino.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--cached", "--name-status"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if proc.returncode != 0 or not proc.stdout:
        return {}
    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        out[parts[-1]] = parts[0][:1]
    return out


def _forbidden_dir_reason(path: str) -> str | None:
    for forbidden in FORBIDDEN_DIRS:
        if not path.startswith(forbidden):
            continue
        if forbidden in ARCHIVE_MESSAGE_DIRS:
            return (
                f"diretório proibido: {forbidden} (PII histórica; "
                f"recriação bloqueada — ADR-319/A34.l6)"
            )
        return f"diretório proibido: {forbidden}"
    return None


def check(path: str, *, staged_statuses: dict[str, str] | None = None) -> str | None:
    """Retorna a razão da violação, ou None se passou.

    `staged_statuses` mapeia paths staged ao status git ("A"/"M"/"D"…);
    deleção staged é limpeza permitida.
    """
    statuses = staged_statuses or {}
    if statuses.get(path) == "D":
        # Remover path proibido do repositório é limpeza, não violação
        # (cleanup A7.6, deleção de _archive/ na A34.l7, remoção de .env).
        return None
    dir_reason = _forbidden_dir_reason(path)
    if dir_reason is not None:
        return dir_reason
    basename = path.rsplit("/", 1)[-1]
    if basename in FORBIDDEN_BASENAMES:
        return f"arquivo proibido: {basename} (em {path})"
    if path in FORBIDDEN_FILES:
        return f"arquivo proibido: {path}"
    for suffix in FORBIDDEN_SUFFIXES:
        if path.endswith(suffix):
            return f"sufixo proibido: {suffix}"
    return None


def main() -> int:
    repo_root = Path.cwd()
    staged = _staged_status_by_path(repo_root)
    violations: list[tuple[str, str]] = []
    for path in sys.argv[1:]:
        reason = check(path, staged_statuses=staged)
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
