#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Avisa se HEAD está em `agent/*` órfã (PR mergeada / branch deletada). Advisory."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys


def _run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def _current_branch() -> str | None:
    rc, out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if rc != 0 or not out or out == "HEAD":
        return None
    return out


def _upstream_name(branch: str) -> str | None:
    rc, out = _run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{u}}"])
    if rc != 0 or not out:
        return None
    return out


def _ref_exists(ref: str) -> bool:
    rc, _ = _run(["git", "rev-parse", "--verify", "--quiet", ref])
    return rc == 0


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


def _diagnose(branch: str) -> tuple[str, dict | None] | None:
    upstream = _upstream_name(branch)
    pr_info = _pr_state_for_branch(branch)
    pr_merged = bool(pr_info and pr_info.get("state") == "MERGED")
    if upstream and _ref_exists(upstream):
        return ("PR já mergeada", pr_info) if pr_merged else None
    reason = (
        "sem upstream remoto"
        if upstream is None
        else f"upstream {upstream} não existe mais no remoto"
    )
    return reason, pr_info


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
