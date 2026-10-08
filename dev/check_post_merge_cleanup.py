#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Avisa se HEAD está em `agent/*` órfã (PR mergeada / branch deletada). Advisory."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Callable


def _run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def _current_branch() -> str | None:
    rc, out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if rc != 0 or not out or out == "HEAD":
        return None
    return out


def _gone_upstream(branch: str) -> str | None:
    # `rev-parse <branch>@{u}` falha igual sem upstream e com upstream [gone]; só o track distingue
    fmt = "%(upstream:short) %(upstream:track,nobracket)"
    rc, out = _run(["git", "for-each-ref", f"--format={fmt}", f"refs/heads/{branch}"])
    name, _, track = out.partition(" ")
    return name if rc == 0 and name and track == "gone" else None


def _gh_pr_json(branch: str) -> str | None:
    if not shutil.which("gh"):
        return None
    rc, out = _run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "all",
            "--limit",
            "1",
            "--json",
            "number,state,mergeCommit,url",
        ]
    )
    return out if rc == 0 and out else None


def _pr_state_for_branch(branch: str) -> dict | None:
    raw = _gh_pr_json(branch)
    if not raw:
        return None
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return items[0] if items else None


def _format_pr_line(pr_info: dict) -> str:
    url = pr_info.get("url", "")
    state = pr_info.get("state", "?")
    merge_sha = (pr_info.get("mergeCommit") or {}).get("oid", "")[:7]
    suffix = f" → {merge_sha}" if merge_sha else ""
    return f"   PR associado: #{pr_info.get('number')} [{state}]{suffix} {url}"


def _print_cleanup(branch: str, reason: str, pr_info: dict | None) -> None:
    print()
    print(f"⚠️  Branch local '{branch}' parece órfã ({reason}).")
    if pr_info:
        print(_format_pr_line(pr_info))
    print("   Limpe e volte para main:")
    print()
    print("     git checkout main && git pull --ff-only \\")
    print(f"       && git branch -D {branch}")
    print()


def _diagnose(
    branch: str, pr_lookup: Callable[[str], dict | None] = _pr_state_for_branch
) -> tuple[str, dict | None] | None:
    # sem upstream é o estado de branch nova, e sem `gh` não há PR para consultar:
    # só PR MERGED ou upstream [gone] provam entrega antes de sugerir `branch -D`
    pr_info = pr_lookup(branch)
    if pr_info and pr_info.get("state") == "MERGED":
        return "PR já mergeada", pr_info
    gone = _gone_upstream(branch)
    if gone:
        return f"upstream {gone} não existe mais no remoto", pr_info
    return None


def main() -> int:
    branch = _current_branch()
    if not branch or not branch.startswith("agent/"):
        return 0
    diagnosis = _diagnose(branch)
    if diagnosis is None:
        return 0
    reason, pr_info = diagnosis
    _print_cleanup(branch, reason, pr_info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
