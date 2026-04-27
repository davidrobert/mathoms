#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev/commit.py — Developer commit helper for the Fin monorepo.

**Ferramenta de desenvolvimento**, não artefato do produto. Foi chamada
`scripts/e_save.py` no mundo CLI single-tenant; migrada para `dev/` para
deixar explícito que é tooling de engenharia, não uma etapa do pipeline.

O pipeline multi-tenant atual persiste dados de usuário em:
  - Banco de dados (Postgres/SQLite via SQLAlchemy + Alembic)
  - Filesystem por tenant em `storage/{workspace_id}/`

Nada disso passa por git. Este script é apenas um atalho com guardrails
para quem está commitando **código-fonte + docs** do repositório.

Preferível ainda assim usar `git` direto com `pre-commit` instalado; este
wrapper serve para quem quer ergonomia (mensagem validada, push em um
comando, dry-run).

Uso:
  python dev/commit.py -m "feat: dashboard card de saldos"
  python dev/commit.py -m "fix(backend): tratar upload vazio"
  python dev/commit.py --dry-run -m "docs: ADR-XYZ"
  python dev/commit.py --no-push -m "chore: bump deps"

Flags:
  -m MESSAGE        Mensagem de commit (obrigatória)
  --dry-run         Mostra o que seria feito, sem commit nem push
  --no-push         Commit local, sem push
  --force           Ignora safety-check de paths/files proibidos (perigoso)

Safety-checks:
  1. Confirma que estamos num repo git
  2. Bloqueia staging de diretórios sensíveis (storage/, data/, inbox/, …)
  3. Bloqueia arquivos sensíveis por nome (.env, mathoms.db, passwords.txt, …)
  4. Valida formato da mensagem (prefixo convencional)
  5. Mostra diff stat antes do commit
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# =============================================================================
# Paths
# =============================================================================
DEV_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DEV_DIR.parent

# Diretórios proibidos de serem commitados (defense-in-depth: todos estão no
# .gitignore, mas se alguém editar o gitignore sem pensar, este check impede
# o vazamento).
#
# - storage/   → árvore backend multi-tenant (storage/<workspace_id>/…)
# - data/      → legado CLI na raiz do repo: extratos/faturas (scripts/)
# - inbox/     → legado CLI: área de entrada
# - inbox_processed/ → legado CLI: processados
# - _scratch/  → temporários
FORBIDDEN_DIRS = (
    "storage/",
    "data/",
    "inbox/",
    "inbox_processed/",
    "_scratch/",
)

# Arquivos individuais que nunca devem ir pro repo.
# `mathoms.db` é o SQLite de dev com dados de vários workspaces;
# `passwords.txt` tem senhas de PDF.
FORBIDDEN_FILES = (
    "mathoms.db",
    "config/passwords.txt",
    # A7.2a (ADR-136): caderno editorial migrou para aggregate Decision.
    "config/decisions.md",
    # A7.4: docs metodológicas movidas de config/ → docs/methodology/. Bloquear
    # ressurgimento dos paths antigos (regressão acidental ou rebase com conflito).
    "config/definitions.md",
    "config/regras_composicao_patrimonial.md",
    "config/source_hierarchy.md",
    "config/milhas.md",
)

# Basenames bloqueados em qualquer diretório — .env/.env.test podem ter secrets
# (FIN_FERNET_KEY, API keys). Regressão: backend/.env vazou pra origin/main
# porque o match era exato e só pegava .env na raiz.
FORBIDDEN_BASENAMES = (
    ".env",
    ".env.test",
)

# Padrões glob-like por sufixo — qualquer *.db é suspeito (backups locais, etc.)
FORBIDDEN_SUFFIXES = (
    ".db",
    ".sqlite",
    ".sqlite3",
)

# Prefixos válidos de mensagem. Em ordem: convencionais (padrão Fin em
# produto web), legados (pipeline CLI, mantidos pra compat com histórico).
# Aceita também escopo opcional entre parênteses: "feat(api): …".
VALID_PREFIXES = [
    # Produto web (atual)
    "feat:",
    "fix:",
    "refactor:",
    "perf:",
    "style:",
    "test:",
    "chore:",
    "backend:",
    "frontend:",
    "api:",
    "db:",
    "infra:",
    "ci:",
    "docs:",
    "update:",
    # Pipeline / CLI legacy (mantidos para histórico e scripts antigos)
    "pipeline:",
    "config:",
    "pre-update:",
    "pre-reset:",
    "E-reset:",
    "E-reset-from-",
    "E1:",
    "E2:",
    "E3:",
    "E4:",
    "E5:",
    "E5.N:",
    "E6:",
    "E6-regen:",
    "E7:",
    "init:",
]

# Regex para aceitar escopo: "feat(api):", "fix(backend/storage):"
_PREFIX_WITH_SCOPE = re.compile(
    r"^(feat|fix|refactor|perf|style|test|chore|backend|frontend|api|db|infra|ci|docs|update|pipeline|config)\([^)]+\):"
)


# =============================================================================
# Logging
# =============================================================================
def log(level: str, message: str) -> None:
    """Imprime mensagem com timestamp no stderr."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "DRY": "🔍"}.get(level, "·")
    print(f"[{timestamp}] {icon} {level}: {message}", file=sys.stderr)


def run_git(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Executa git no PROJECT_DIR."""
    cmd = ["git", "-C", str(PROJECT_DIR)] + list(args)
    return subprocess.run(cmd, capture_output=capture, text=True, check=check)


# =============================================================================
# Safety-checks
# =============================================================================
def verify_git_repo() -> bool:
    try:
        result = run_git("rev-parse", "--is-inside-work-tree")
        return result.stdout.strip() == "true"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_status() -> str:
    result = run_git("status", "--short")
    return result.stdout


def get_diff_stat() -> str:
    result = run_git("diff", "--stat", "--cached", check=False)
    return result.stdout


def _parse_status_short_line(line: str) -> tuple[str, str, str] | None:
    """Retorna (path, index_status, worktree_status) ou None para linhas ignoradas."""
    line = line.rstrip()
    if not line or line.startswith("## "):
        return None
    if line.startswith("?? ") or line.startswith("!! "):
        return (line[3:].strip().strip('"'), "?", "?")
    if len(line) < 4:
        return None
    idx, wt = line[0], line[1]
    rest = line[3:].strip()
    if " -> " in rest:
        rest = rest.split(" -> ", 1)[1]
    path = rest.strip('"')
    return (path, idx, wt)


def check_forbidden_paths(status_output: str) -> list[tuple[str, str]]:
    """Retorna lista de (path, motivo) violando FORBIDDEN_{DIRS,FILES,BASENAMES,SUFFIXES}."""
    violations: list[tuple[str, str]] = []
    for line in status_output.strip().splitlines():
        parsed = _parse_status_short_line(line)
        if parsed is None:
            continue
        path, idx, wt = parsed
        basename = path.rsplit("/", 1)[-1]
        is_deletion = idx == "D" or wt == "D"
        # Remover arquivo proibido do repositório é desejável — não bloquear deletes.
        if is_deletion and (path in FORBIDDEN_FILES or basename in FORBIDDEN_BASENAMES):
            continue
        for forbidden in FORBIDDEN_DIRS:
            if path.startswith(forbidden):
                violations.append((path, f"diretório proibido: {forbidden}"))
                break
        else:
            if basename in FORBIDDEN_BASENAMES:
                violations.append((path, f"arquivo proibido: {basename} (em {path})"))
                continue
            if path in FORBIDDEN_FILES:
                violations.append((path, f"arquivo proibido: {path}"))
                continue
            for suffix in FORBIDDEN_SUFFIXES:
                if path.endswith(suffix):
                    violations.append((path, f"sufixo proibido: {suffix}"))
                    break
    return violations


def validate_commit_message(message: str) -> tuple[bool, str]:
    message = message.strip()
    if not message:
        return False, "Mensagem vazia"
    if len(message) < 5:
        return False, "Mensagem muito curta (mínimo 5 caracteres)"

    # Aceita prefixo com escopo (feat(api):, …)
    if _PREFIX_WITH_SCOPE.match(message):
        return True, "OK"

    # Aceita prefixos simples da lista
    if any(message.startswith(p) for p in VALID_PREFIXES):
        return True, "OK"

    return False, (
        "Prefixo inválido.\n"
        f"    Aceitos: {', '.join(VALID_PREFIXES[:10])}…\n"
        "    Exemplos: 'feat: …', 'fix(api): …', 'docs: …', 'pipeline: …'"
    )


# =============================================================================
# Git ops
# =============================================================================
def stage_all() -> str:
    run_git("add", "-A")
    return get_status()


def commit(message: str) -> bool:
    try:
        run_git("commit", "-m", message)
        log("OK", "Commit criado")
        hash_result = run_git("log", "--oneline", "-1")
        log("INFO", f"  → {hash_result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        text = (e.stdout or "") + (e.stderr or "")
        if any(
            s in text
            for s in (
                "nothing to commit",
                "nada para submeter",
                "nada a submeter",
                "nothing added to commit",
            )
        ):
            log("WARN", "Nada para comitar — working tree limpa")
            return False
        log("ERROR", f"Commit falhou: {e.stderr or e.stdout}")
        return False


def push() -> bool:
    try:
        branch_result = run_git("rev-parse", "--abbrev-ref", "HEAD", check=False)
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"
        log("INFO", f"Pushing para origin/{current_branch}…")
        run_git("push", "origin", current_branch, capture=False)
        log("OK", "Push concluído")
        return True
    except subprocess.CalledProcessError:
        log("ERROR", "Push falhou — possível divergência com o remote")
        log("INFO", "  Tente: git pull --rebase origin <branch>  e rode o commit novamente")
        return False


def show_recent_log() -> None:
    result = run_git("log", "--oneline", "-3")
    log("INFO", "Últimos commits:")
    for line in result.stdout.strip().splitlines():
        print(f"    {line}", file=sys.stderr)


# =============================================================================
# CLI
# =============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="dev/commit.py — commit & push helper (tooling de dev, não produto)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python dev/commit.py -m "feat: dashboard card de saldos"
  python dev/commit.py -m "fix(api): validar upload vazio" --no-push
  python dev/commit.py --dry-run -m "docs: ADR-068"
        """,
    )
    parser.add_argument("-m", "--message", required=True, help="Mensagem de commit")
    parser.add_argument("--dry-run", action="store_true", help="Mostra sem executar")
    parser.add_argument("--no-push", action="store_true", help="Commit local, sem push")
    parser.add_argument("--force", action="store_true", help="Ignora safety-check (perigoso)")

    args = parser.parse_args()
    dry = args.dry_run
    prefix = "DRY" if dry else "INFO"

    print("=" * 60, file=sys.stderr)
    log(prefix, "dev/commit.py — commit & push")
    print("=" * 60, file=sys.stderr)

    # 1. Repo
    if not verify_git_repo():
        log("ERROR", f"Não é um repositório git: {PROJECT_DIR}")
        sys.exit(1)
    log("OK", f"Repositório: {PROJECT_DIR.name}")

    # 2. Mensagem
    valid, reason = validate_commit_message(args.message)
    if not valid:
        log("ERROR", reason)
        sys.exit(1)
    log("OK", f'Mensagem: "{args.message}"')

    # 3. Status
    status_before = get_status()
    if not status_before.strip():
        log("WARN", "Working tree limpa — nada para comitar")
        sys.exit(0)

    log(prefix, f"Arquivos alterados ({len(status_before.strip().splitlines())}):")
    for line in status_before.strip().splitlines():
        print(f"    {line}", file=sys.stderr)

    # 4. Safety-check
    violations = check_forbidden_paths(status_before)
    if violations:
        log("ERROR", f"Paths proibidos detectados ({len(violations)}):")
        for path, reason in violations:
            print(f"    ✗ {path} — {reason}", file=sys.stderr)
        if not args.force:
            log("ERROR", "Abortando. Verifique o .gitignore ou use --force (não recomendado).")
            sys.exit(1)
        log("WARN", "--force: prosseguindo apesar dos avisos")

    # 5. Dry-run preview
    if dry:
        log("DRY", "Executaria: git add -A")
        diff_stat = get_diff_stat()
        if diff_stat.strip():
            log("DRY", "Diff stat:")
            for line in diff_stat.strip().splitlines():
                print(f"    {line}", file=sys.stderr)
        log("DRY", f'Executaria: git commit -m "{args.message}"')
        if not args.no_push:
            log("DRY", "Executaria: git push origin <branch>")
        else:
            log("DRY", "Push pulado (--no-push)")
        print("=" * 60, file=sys.stderr)
        log("DRY", "Nenhuma alteração feita (dry-run)")
        sys.exit(0)

    # 6. Stage + recheck
    log("INFO", "Staging: git add -A")
    status_after = stage_all()
    violations_post = check_forbidden_paths(status_after)
    if violations_post and not args.force:
        log("ERROR", "Paths proibidos ainda presentes após staging — abortando")
        run_git("reset", "HEAD", check=False)
        sys.exit(1)

    # 7. Commit
    if not commit(args.message):
        sys.exit(0)

    # 8. Push
    if args.no_push:
        log("INFO", "Push pulado (--no-push)")
    else:
        if not push():
            sys.exit(1)

    # 9. Confirm
    print("-" * 60, file=sys.stderr)
    show_recent_log()
    print("=" * 60, file=sys.stderr)
    log("OK", "commit concluído")


if __name__ == "__main__":
    main()
