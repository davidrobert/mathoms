#!/usr/bin/env python3
"""Rebaseline de golden em commit ISOLADO de código de produção (G-c · F2-DB5); exit 1 = commit misto."""

# Disciplina de rebaseline (DATA_LINEAGE §Guard-rails G-c): um commit que toca
# golden (`tests/fixtures/pipeline_golden/**`, incl. rebaseline_manifest.yaml —
# viajam juntos) E código de produção (`pipeline/**`, `scripts/**`,
# `backend/app/**`) cimentaria o valor novo junto da mudança que o produziu,
# sem diff auditável. Granularidade POR COMMIT (não por PR-diff): é o que
# permite o fluxo legítimo "PR com N commits, 1 deles é o rebaseline isolado".
# Name-only (paths tocados), nunca conteúdo. `config/schemas/**` e `tests/**`
# NÃO contam como produção: mudar contrato+golden no mesmo commit é o próprio
# fluxo de remoção de campo (F2-DB1).
#
# Modos: --staged (pre-commit, diff em cache) | --commit-range BASE..HEAD (CI,
# valida cada commit do range isoladamente).

from __future__ import annotations

import argparse
import subprocess
import sys

_GOLDEN_PREFIX = "tests/fixtures/pipeline_golden/"
_PRODUCTION_PREFIXES = ("pipeline/", "scripts/", "backend/app/")


def is_golden(path: str) -> bool:
    return path.startswith(_GOLDEN_PREFIX)


def is_production(path: str) -> bool:
    return path.startswith(_PRODUCTION_PREFIXES)


def violation(paths: list[str]) -> str | None:
    """Retorna descrição da violação se a lista mistura golden + produção."""
    golden = sorted(p for p in paths if is_golden(p))
    production = sorted(p for p in paths if is_production(p))
    if not golden or not production:
        return None
    return (
        f"golden ({', '.join(golden[:3])}{'…' if len(golden) > 3 else ''}) junto de "
        f"produção ({', '.join(production[:3])}{'…' if len(production) > 3 else ''}) — "
        "separe o rebaseline em commit próprio (label golden-rebaseline, G-c)"
    )


def _git_lines(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def _staged_paths() -> list[str]:
    return _git_lines("diff", "--cached", "--name-only")


def _commit_paths(sha: str) -> list[str]:
    return _git_lines("diff-tree", "--no-commit-id", "--name-only", "-r", sha)


def check_staged() -> list[str]:
    msg = violation(_staged_paths())
    return [f"staged: {msg}"] if msg else []


def check_commit_range(commit_range: str) -> list[str]:
    errors: list[str] = []
    for sha in _git_lines("rev-list", "--no-merges", commit_range):
        msg = violation(_commit_paths(sha))
        if msg:
            errors.append(f"{sha[:10]}: {msg}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit-range", default=None, help="BASE..HEAD (CI); default: staged")
    args = parser.parse_args(argv)

    errors = check_commit_range(args.commit_range) if args.commit_range else check_staged()
    for line in errors:
        print(f"check_golden_rebaseline_isolation: {line}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
