#!/usr/bin/env python3
"""Skip-class de jobs pesados quando o update-branch só trouxe docs (ADR-322).

Fail-closed: rebase (1 parent), mix de código, OpenAPI, smoke velho ou
ausente → não skipa. O nightly/`main-smoke` morto deixa o skip inerte.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_PREFIX = "docs/reference/api/"
SMOKE_WORKFLOWS = frozenset({"Nightly", "Main smoke"})
SMOKE_MAX_AGE = timedelta(hours=24)


def is_docs_only_path(path: str) -> bool:
    """True se o path é vault/markdown de raiz, e não contrato de API."""
    normalized = path.replace("\\", "/").lstrip("./")
    if not normalized or normalized.endswith("/"):
        return False
    if normalized.startswith(API_PREFIX):
        return False
    if normalized.startswith("docs/"):
        return True
    return "/" not in normalized and normalized.endswith(".md")


def paths_are_docs_only(paths: Sequence[str]) -> bool:
    """False se a lista é vazia (desconhecido) ou tem qualquer não-doc."""
    if not paths:
        return False
    return all(is_docs_only_path(p) for p in paths)


def smoke_is_fresh(runs: Sequence[dict[str, object]], *, now: datetime | None = None) -> bool:
    """True se um run success de Nightly/Main smoke cabe em 24h."""
    clock = now or datetime.now(timezone.utc)
    for run in runs:
        if run.get("name") not in SMOKE_WORKFLOWS:
            continue
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            continue
        stamped = _parse_iso(str(run.get("updatedAt") or ""))
        if stamped is None:
            continue
        if clock - stamped <= SMOKE_MAX_AGE:
            return True
    return False


def should_skip_heavy_jobs(
    *,
    is_merge_commit: bool,
    second_parent_on_main: bool,
    paths: Sequence[str],
    smoke_fresh: bool,
) -> bool:
    """AND de todos os predicados — qualquer buraco vira suíte cheia."""
    if not is_merge_commit or not second_parent_on_main:
        return False
    if not paths_are_docs_only(paths):
        return False
    return smoke_fresh


def decide(repo: Path, smoke_runs: Sequence[dict[str, object]]) -> bool:
    """Combina git local + liveness do smoke (injetável nos testes)."""
    if _parent_count(repo) != 2 or not _second_parent_on_main(repo):
        return False
    return should_skip_heavy_jobs(
        is_merge_commit=True,
        second_parent_on_main=True,
        paths=_incoming_paths(repo),
        smoke_fresh=smoke_is_fresh(smoke_runs),
    )


def fetch_smoke_runs() -> list[dict[str, object]]:
    """Lista runs recentes em main. Qualquer falha de I/O vira lista vazia."""
    proc = _gh_run_list()
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _gh_run_list() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--branch",
            "main",
            "--limit",
            "20",
            "--json",
            "name,status,conclusion,updatedAt",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_iso(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _parent_count(repo: Path) -> int:
    proc = _git(repo, "rev-list", "--parents", "-n", "1", "HEAD")
    if proc.returncode != 0 or not proc.stdout.strip():
        return 0
    return len(proc.stdout.split()) - 1


def _second_parent_on_main(repo: Path) -> bool:
    second = _git(repo, "rev-parse", "HEAD^2")
    if second.returncode != 0:
        return False
    tip = _git(repo, "rev-parse", "origin/main")
    if tip.returncode != 0:
        return False
    check = _git(repo, "merge-base", "--is-ancestor", second.stdout.strip(), "origin/main")
    return check.returncode == 0


def _incoming_paths(repo: Path) -> tuple[str, ...]:
    proc = _git(repo, "diff", "--name-only", "-z", "HEAD^1", "HEAD")
    if proc.returncode != 0 or not proc.stdout:
        return ()
    return tuple(p for p in proc.stdout.split("\0") if p)


def _write_github_output(skip: bool) -> None:
    line = f"incoming_main_docs_only={'true' if skip else 'false'}\n"
    target = os.environ.get("GITHUB_OUTPUT")
    if not target:
        print(line, end="")
        return
    with Path(target).open("a", encoding="utf-8") as fh:
        fh.write(line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", type=Path)
    parser.add_argument("--github-output", action="store_true")
    args = parser.parse_args()
    skip = decide(args.repo.resolve(), fetch_smoke_runs())
    if args.github_output:
        _write_github_output(skip)
    else:
        print("true" if skip else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
