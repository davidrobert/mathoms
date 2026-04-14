#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E-save — Deterministic commit & push to remote

Performs a safety-checked git add + commit + push for the financas-familia repo.

Usage:
  python scripts/e_save.py -m "pipeline: ciclo mar/2026 — relatório gerado"
  python scripts/e_save.py -m "config: definitions.md — nova keyword"
  python scripts/e_save.py --dry-run -m "docs: manual v4.8"
  python scripts/e_save.py --no-push -m "fix: e4_categorize.py — normalização"

Flags:
  -m MESSAGE        Commit message (required)
  --dry-run         Show what would be committed, but don't commit or push
  --no-push         Commit locally but skip git push
  --force-add       Use 'git add -A' even if safety check warns (not recommended)

Safety checks:
  1. Verifies we are inside the financas-familia git repo
  2. Checks that no files from data/, inbox/, inbox_processed/ are staged
  3. Shows diff stats before committing
  4. Validates commit message follows convention

Author: Claude Opus 4.6
Date: 2026-04-05
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# =============================================================================
# Paths
# =============================================================================
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent

# Directories that must NEVER be committed (even if .gitignore fails)
FORBIDDEN_DIRS = {"data/", "inbox/", "inbox_processed/"}

# Valid commit message prefixes (from manual 4.5.3 convention)
VALID_PREFIXES = [
    "pipeline:", "config:", "docs:", "fix:", "update:",
    "pre-update:", "pre-reset:", "E-reset:", "E-reset-from-",
    "E1:", "E2:", "E3:", "E4:", "E5:", "E5.N:", "E6:",
    "E6-regen:", "refactor:", "init:",
]


# =============================================================================
# Logging
# =============================================================================
def log(level: str, message: str) -> None:
    """Print a timestamped message to stderr."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "DRY": "🔍"}.get(level, "·")
    print(f"[{timestamp}] {icon} {level}: {message}", file=sys.stderr)


def run_git(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a git command from the project directory."""
    cmd = ["git", "-C", str(PROJECT_DIR)] + list(args)
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )


# =============================================================================
# Safety checks
# =============================================================================
def verify_git_repo() -> bool:
    """Ensure we're inside a git repository."""
    try:
        result = run_git("rev-parse", "--is-inside-work-tree")
        return result.stdout.strip() == "true"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_status() -> str:
    """Get git status --short output."""
    result = run_git("status", "--short")
    return result.stdout


def get_diff_stat() -> str:
    """Get diff stat for staged + unstaged changes."""
    result = run_git("diff", "--stat", "--cached", check=False)
    return result.stdout


def check_forbidden_files(status_output: str) -> list[str]:
    """Check if any forbidden directory files appear in git status."""
    violations = []
    for line in status_output.strip().splitlines():
        if not line.strip():
            continue
        # git status --short format: "XY filename" or "XY filename -> newname"
        file_path = line[3:].strip().split(" -> ")[0]
        for forbidden in FORBIDDEN_DIRS:
            if file_path.startswith(forbidden):
                violations.append(file_path)
    return violations


def validate_commit_message(message: str) -> tuple[bool, str]:
    """Validate commit message follows the convention."""
    message = message.strip()
    if not message:
        return False, "Mensagem de commit vazia"
    if len(message) < 5:
        return False, "Mensagem muito curta (mínimo 5 caracteres)"

    # Check prefix convention
    has_valid_prefix = any(message.startswith(p) for p in VALID_PREFIXES)
    if not has_valid_prefix:
        prefixes_str = ", ".join(VALID_PREFIXES[:6]) + "..."
        return False, (
            f"Mensagem não segue a convenção de prefixos.\n"
            f"  Prefixos válidos: {prefixes_str}\n"
            f"  Exemplo: pipeline: ciclo mar/2026 — relatório gerado"
        )
    return True, "OK"


# =============================================================================
# Main operations
# =============================================================================
def stage_all() -> str:
    """Run git add -A and return new status."""
    run_git("add", "-A")
    return get_status()


def commit(message: str) -> bool:
    """Create a git commit. Returns True on success."""
    try:
        result = run_git("commit", "-m", message)
        log("OK", "Commit criado com sucesso")
        # Print commit hash
        hash_result = run_git("log", "--oneline", "-1")
        log("INFO", f"  → {hash_result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        output_text = (e.stdout or "") + (e.stderr or "")
        if "nothing to commit" in output_text or "nada para submeter" in output_text or "nada a submeter" in output_text or "nothing added to commit" in output_text:
            log("WARN", "Nada para comitar — working tree limpa")
            return False
        log("ERROR", f"Commit falhou: {e.stderr or e.stdout}")
        return False


def push() -> bool:
    """Push to origin. Returns True on success."""
    try:
        # Detecta branch atual
        branch_result = run_git("rev-parse", "--abbrev-ref", "HEAD", check=False)
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"

        log("INFO", "Pushing para origin...")
        result = run_git("push", "origin", current_branch, capture=False)
        log("OK", "Push concluído")
        return True
    except subprocess.CalledProcessError:
        log("ERROR", "Push falhou — possível divergência com remote")
        log("INFO", f"  Tente: git -C financas-familia pull --rebase origin {current_branch}")
        log("INFO", "  Depois: python scripts/e_save.py -m \"[mesma mensagem]\"")
        return False


def show_recent_log() -> None:
    """Show last 3 commits for confirmation."""
    result = run_git("log", "--oneline", "-3")
    log("INFO", "Últimos commits:")
    for line in result.stdout.strip().splitlines():
        print(f"    {line}", file=sys.stderr)


# =============================================================================
# CLI
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="E-save: commit & push determinístico para financas-familia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/e_save.py -m "pipeline: ciclo mar/2026 — relatório gerado"
  python scripts/e_save.py -m "config: definitions.md — nova keyword" --no-push
  python scripts/e_save.py -m "docs: manual v4.8" --dry-run
        """,
    )
    parser.add_argument("-m", "--message", required=True, help="Mensagem de commit")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra o que seria feito")
    parser.add_argument("--no-push", action="store_true", help="Commit local, sem push")
    parser.add_argument("--force-add", action="store_true", help="Ignorar safety check de arquivos proibidos")

    args = parser.parse_args()
    dry = args.dry_run
    prefix = "DRY" if dry else "INFO"

    print("=" * 60, file=sys.stderr)
    log(prefix, "E-save — Commit & Push")
    print("=" * 60, file=sys.stderr)

    # --- Step 1: Verify git repo ---
    if not verify_git_repo():
        log("ERROR", f"Não é um repositório Git: {PROJECT_DIR}")
        sys.exit(1)
    log("OK", f"Repositório Git confirmado: {PROJECT_DIR.name}")

    # --- Step 2: Validate commit message ---
    valid, reason = validate_commit_message(args.message)
    if not valid:
        log("ERROR", f"Mensagem inválida: {reason}")
        log("INFO", f"Prefixos válidos: {', '.join(VALID_PREFIXES)}")
        sys.exit(1)
    log("OK", f"Mensagem: \"{args.message}\"")

    # --- Step 3: Check current status ---
    status_before = get_status()
    if not status_before.strip():
        log("WARN", "Working tree limpa — nada para comitar")
        sys.exit(0)

    log(prefix, f"Arquivos alterados ({len(status_before.strip().splitlines())}):")
    for line in status_before.strip().splitlines():
        print(f"    {line}", file=sys.stderr)

    # --- Step 4: Safety check — forbidden dirs ---
    violations = check_forbidden_files(status_before)
    if violations:
        log("WARN", f"Arquivos em diretórios proibidos detectados ({len(violations)}):")
        for v in violations:
            print(f"    ✗ {v}", file=sys.stderr)
        if not args.force_add:
            log("ERROR", "Abortando. Use --force-add para ignorar (não recomendado)")
            log("INFO", "Verifique o .gitignore — esses arquivos não deveriam aparecer")
            sys.exit(1)
        else:
            log("WARN", "--force-add: prosseguindo apesar dos avisos")

    # --- Step 5: Stage ---
    if dry:
        log("DRY", "Executaria: git add -A")
        diff_stat = get_diff_stat()
        if diff_stat.strip():
            log("DRY", "Diff stat:")
            for line in diff_stat.strip().splitlines():
                print(f"    {line}", file=sys.stderr)
        log("DRY", f"Executaria: git commit -m \"{args.message}\"")
        if not args.no_push:
            log("DRY", "Executaria: git push origin main")
        else:
            log("DRY", "Push pulado (--no-push)")
        print("=" * 60, file=sys.stderr)
        log("DRY", "Nenhuma alteração feita (dry-run)")
        sys.exit(0)

    # --- Step 5 (real): Stage all ---
    log("INFO", "Staging: git add -A")
    status_after = stage_all()

    # Re-check forbidden after staging
    violations_post = check_forbidden_files(status_after)
    if violations_post and not args.force_add:
        log("ERROR", "Arquivos proibidos ainda presentes após staging — abortando")
        run_git("reset", "HEAD", check=False)
        sys.exit(1)

    # --- Step 6: Commit ---
    log("INFO", "Criando commit...")
    if not commit(args.message):
        sys.exit(0)  # nothing to commit is not an error

    # --- Step 7: Push ---
    if args.no_push:
        log("INFO", "Push pulado (--no-push)")
    else:
        if not push():
            sys.exit(1)

    # --- Step 8: Confirm ---
    print("-" * 60, file=sys.stderr)
    show_recent_log()
    print("=" * 60, file=sys.stderr)
    log("OK", "E-save concluído com sucesso")


if __name__ == "__main__":
    main()
