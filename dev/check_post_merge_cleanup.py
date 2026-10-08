#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Avisa se HEAD está em `agent/*` órfã; só manda apagar o que já foi publicado. Advisory."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from typing import NamedTuple

try:  # script direto vs. import como `dev.*` (padrão de dev/lane_pickup.py)
    import _lane_branch_delivery as _delivery  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover
    from dev import _lane_branch_delivery as _delivery  # noqa: E402

PrLookup = Callable[[str], dict | None]
Classifier = Callable[[list[str]], tuple[list[str], list[str], list[str]]]


class Diagnosis(NamedTuple):
    """`unpublished`: 0 libera o `branch -D`; N conta commits fora do PR; None é sem prova."""

    reason: str
    pr_info: dict | None
    unpublished: int | None


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
            "number,state,mergeCommit,headRefOid,url",
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


def _orphan_reason(branch: str, pr_info: dict | None) -> str | None:
    # sem upstream é o estado de branch nova, e sem `gh` não há PR para consultar:
    # só PR MERGED ou upstream [gone] provam entrega antes de sugerir `branch -D`
    if pr_info and pr_info.get("state") == "MERGED":
        return "PR já mergeada"
    gone = _gone_upstream(branch)
    return f"upstream {gone} não existe mais no remoto" if gone else None


def _merged_pr_head(pr_info: dict | None) -> str | None:
    if not pr_info or pr_info.get("state") != "MERGED":
        return None
    return pr_info.get("headRefOid") or None


def _commits_beyond_head(branch: str, head: str) -> int | None:
    """Commits do tip local fora do head do PR; None se o head não está no clone."""
    rc, out = _run(["git", "rev-list", "--count", f"{head}..refs/heads/{branch}"])
    return int(out) if rc == 0 and out.isdigit() else None


def _delivered_to_main(branch: str, classify: Classifier) -> bool:
    _alive, delivered, _blind = classify([f"refs/heads/{branch}"])
    return bool(delivered)


def _unpublished(branch: str, pr_info: dict | None, classify: Classifier) -> int | None:
    # entrega prova o que foi publicado, não o que veio depois: commit feito após o
    # push/merge só existe no clone. Sem head do PR (upstream [gone] já podado), a
    # ponta publicada é irrecuperável — vale só o tip já estar em origin/main
    head = _merged_pr_head(pr_info)
    beyond = _commits_beyond_head(branch, head) if head else None
    if beyond == 0 or _delivered_to_main(branch, classify):
        return 0
    return beyond


def _diagnose(
    branch: str,
    pr_lookup: PrLookup = _pr_state_for_branch,
    classify: Classifier = _delivery.classificar,
) -> Diagnosis | None:
    pr_info = pr_lookup(branch)
    reason = _orphan_reason(branch, pr_info)
    if reason is None:
        return None
    return Diagnosis(reason, pr_info, _unpublished(branch, pr_info, classify))


def _format_pr_line(pr_info: dict) -> str:
    url = pr_info.get("url", "")
    state = pr_info.get("state", "?")
    merge_sha = (pr_info.get("mergeCommit") or {}).get("oid", "")[:7]
    suffix = f" → {merge_sha}" if merge_sha else ""
    return f"   PR associado: #{pr_info.get('number')} [{state}]{suffix} {url}"


def _print_header(branch: str, diagnosis: Diagnosis, caveat: str = "") -> None:
    print()
    print(f"⚠️  Branch local '{branch}' parece órfã ({diagnosis.reason}){caveat}.")
    if diagnosis.pr_info:
        print(_format_pr_line(diagnosis.pr_info))


def _print_delete(branch: str, diagnosis: Diagnosis) -> None:
    _print_header(branch, diagnosis)
    print("   Limpe e volte para main:")
    print()
    print("     git checkout main && git pull --ff-only \\")
    print(f"       && git branch -D {branch}")
    print()


def _print_rescue(branch: str, diagnosis: Diagnosis) -> None:
    head = _merged_pr_head(diagnosis.pr_info) or ""
    caveat = f", mas tem {diagnosis.unpublished} commit(s) local(is) que não entraram no PR"
    _print_header(branch, diagnosis, caveat)
    print("   Não apague a branch: leve esses commits para uma branch nova a partir de main:")
    print()
    print("     git fetch origin && git switch -c agent/<slug>/<yyyyMMdd-HHmm> origin/main \\")
    print(f"       && git cherry-pick {head[:12]}..{branch}")
    print()


def _print_unproven(branch: str, diagnosis: Diagnosis) -> None:
    _print_header(branch, diagnosis, ", mas o conteúdo do tip local não está em origin/main")
    print("   Não apague a branch sem conferir o que só existe aqui")
    print("   (ou origin/main está velho: `git fetch origin` e rode de novo):")
    print()
    print(f"     git log --oneline origin/main..{branch}")
    print()


def _print_diagnosis(branch: str, diagnosis: Diagnosis) -> None:
    if diagnosis.unpublished == 0:
        _print_delete(branch, diagnosis)
    elif diagnosis.unpublished is None:
        _print_unproven(branch, diagnosis)
    else:
        _print_rescue(branch, diagnosis)


def main() -> int:
    branch = _current_branch()
    if not branch or not branch.startswith("agent/"):
        return 0
    diagnosis = _diagnose(branch)
    if diagnosis is not None:
        _print_diagnosis(branch, diagnosis)
    return 0


if __name__ == "__main__":
    sys.exit(main())
