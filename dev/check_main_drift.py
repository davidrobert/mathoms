#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev/check_main_drift.py — hook pre-push.

Bloqueia `git push origin main` quando `origin/main` já avançou além do
HEAD local, forçando o agente a rebasar antes de pushar. Sem esse gate,
o push é rejeitado por non-fast-forward e o agente é tentado a
`--force` (proibido em main).

Para outras branches (`agent/*`, feature), apenas **avisa** se a branch
está muito atrás de main — não bloqueia.

Uso: invocado automaticamente por `pre-commit` como hook de stage
`pre-push`. Lê linhas no formato padrão do git pre-push via stdin:

    <local_ref> <local_sha> <remote_ref> <remote_sha>

Bypass manual (apenas para emergências): `MATHOMS_SKIP_DRIFT_CHECK=1`.

Ver CLAUDE.md §"Protocolo obrigatório" item 5.
"""

from __future__ import annotations

import os
import subprocess
import sys


MAIN_REF = "refs/heads/main"
DRIFT_WARN_THRESHOLD = 5  # branches feature: aviso informativo acima disso


def _run(cmd: list[str]) -> tuple[int, str]:
    """Roda comando git, retorna (returncode, stdout_strip)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def _count_ahead(base: str, head: str) -> int:
    """Conta commits em `base` que não estão em `head` (base..head equivalente)."""
    rc, out = _run(["git", "rev-list", "--count", f"{head}..{base}"])
    if rc != 0 or not out.isdigit():
        return 0
    return int(out)


def _fetch_origin() -> bool:
    """Fetch origin silenciosamente. Retorna True se sucesso."""
    rc, _ = _run(["git", "fetch", "origin", "--quiet"])
    return rc == 0


def _check_push_to_main(local_sha: str) -> int:
    """Valida push para main. Retorna exit code (0 ok, 1 bloqueia)."""
    drift = _count_ahead("origin/main", local_sha)
    if drift == 0:
        return 0

    print(
        "\n🛑 pre-push bloqueado: origin/main avançou "
        f"{drift} commit(s) além do HEAD local.",
        file=sys.stderr,
    )
    print(
        "\nAntes de pushar para main, rode:\n"
        "  git fetch origin\n"
        "  git rebase origin/main\n"
        "  pytest backend/tests -q   # regressão silenciosa\n"
        "\nBypass (emergência): MATHOMS_SKIP_DRIFT_CHECK=1 git push ...\n"
        "Ver CLAUDE.md §'Protocolo obrigatório' item 5.",
        file=sys.stderr,
    )
    return 1


def _warn_push_to_feature(local_ref: str, local_sha: str) -> int:
    """Avisa se branch feature está muito atrás de main. Nunca bloqueia."""
    drift = _count_ahead("origin/main", local_sha)
    if drift >= DRIFT_WARN_THRESHOLD:
        print(
            f"ℹ️  {local_ref} está {drift} commit(s) atrás de origin/main.",
            file=sys.stderr,
        )
        print(
            "   Considere `git rebase origin/main` antes do próximo push "
            "(CLAUDE.md §'Protocolo obrigatório' item 6).",
            file=sys.stderr,
        )
    return 0


def main() -> int:
    if os.environ.get("MATHOMS_SKIP_DRIFT_CHECK"):
        return 0

    # pre-push envia via stdin uma linha por ref sendo pushada:
    # <local_ref> <local_sha> <remote_ref> <remote_sha>
    refs = [ln.strip() for ln in sys.stdin.readlines() if ln.strip()]
    if not refs:
        return 0  # nada a pushar

    if not _fetch_origin():
        print(
            "⚠️  pre-push drift check: git fetch origin falhou; "
            "pulando validação.",
            file=sys.stderr,
        )
        return 0

    exit_code = 0
    for line in refs:
        parts = line.split()
        if len(parts) < 4:
            continue
        local_ref, local_sha, remote_ref, _remote_sha = parts[:4]
        if local_sha == "0" * 40:
            continue  # delete de branch remota

        if remote_ref == MAIN_REF:
            exit_code |= _check_push_to_main(local_sha)
        else:
            _warn_push_to_feature(local_ref, local_sha)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
