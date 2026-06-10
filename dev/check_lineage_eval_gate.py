#!/usr/bin/env python3
"""Gate determinístico de PR do eval de lineage (ADR-281 · A25.l4 F7): falha quando o PR toca a superfície de lineage (``pipeline/domain/services/lineage_*``, ``lineage_registry.py`` ou ``config/prompts/lineage_debug.yaml``) ENQUANTO existe Issue aberta com label ``lineage-eval-fail`` (nightly vermelho) — corrija o eval antes de mexer na superfície; offline/sem ``gh`` degrada para pass com warning."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

WATCHED_PREFIXES = (
    "pipeline/domain/services/lineage_",
    "pipeline/domain/lineage_registry.py",
    "config/prompts/lineage_debug.yaml",
)
ISSUE_LABEL = "lineage-eval-fail"
_PR_REF_RE = re.compile(r"^refs/pull/(\d+)/")


def watched_files(changed: list[str]) -> list[str]:
    return [f for f in changed if f.startswith(WATCHED_PREFIXES)]


def _run(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _changed_via_gh_pr() -> list[str] | None:
    match = _PR_REF_RE.match(os.environ.get("GITHUB_REF", ""))
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not match or not repo:
        return None
    out = _run(
        [
            "gh",
            "api",
            f"repos/{repo}/pulls/{match.group(1)}/files",
            "--paginate",
            "--jq",
            ".[].filename",
        ]
    )
    return out.splitlines() if out is not None else None


def _changed_via_git() -> list[str] | None:
    for base in ("origin/main...HEAD", "HEAD~1"):
        out = _run(["git", "diff", "--name-only", base])
        if out is not None:
            return out.splitlines()
    return None


def changed_files() -> list[str] | None:
    """PR no CI → gh api; local → git diff; irresolúvel → None (pass gracioso)."""
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        from_pr = _changed_via_gh_pr()
        if from_pr is not None:
            return from_pr
    return _changed_via_git()


def open_failure_issues() -> list[dict] | None:
    out = _run(
        ["gh", "issue", "list", "--label", ISSUE_LABEL, "--state", "open", "--json", "number,title"]
    )
    if out is None:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def _report_violation(touched: list[str], issues: list[dict]) -> None:
    for issue in issues:
        print(
            f"check_lineage_eval_gate: Issue #{issue['number']} aberta "
            f"({ISSUE_LABEL}): {issue['title']}",
            file=sys.stderr,
        )
    print(
        "check_lineage_eval_gate: PR toca "
        + ", ".join(touched)
        + " com eval de lineage vermelho — corrija o nightly (ou feche a Issue) antes",
        file=sys.stderr,
    )


def main() -> int:
    changed = changed_files()
    if changed is None:
        print("check_lineage_eval_gate: diff irresolúvel (offline?) — pass gracioso")
        return 0
    touched = watched_files(changed)
    if not touched:
        print("check_lineage_eval_gate: OK (PR não toca superfície de lineage)")
        return 0
    issues = open_failure_issues()
    if issues is None:
        print("check_lineage_eval_gate: gh indisponível — pass gracioso (offline)")
        return 0
    if not issues:
        print(f"check_lineage_eval_gate: OK ({len(touched)} arquivo(s) de lineage, eval verde)")
        return 0
    _report_violation(touched, issues)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
