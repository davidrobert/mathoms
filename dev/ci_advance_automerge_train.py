#!/usr/bin/env python3
"""Avança o trem de auto-merge (ADR-322): update-branch em exatamente 1 PR por
invocação. Uso local (identidade do `gh auth`): python3 dev/ci_advance_automerge_train.py [--dry-run]"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from typing import Any

EXCLUDED_LABELS = {"wip", "do-not-merge", "blocked"}
REQUIRED_CONTEXTS = {"All checks green", "Title (Conventional Commits)"}
PR_LIST_FIELDS = (
    "number,title,createdAt,isDraft,labels,mergeStateStatus,autoMergeRequest,statusCheckRollup"
)


def _gh(*args: str) -> str:
    """gh CLI com 1 retry (backoff 5s) — API do GitHub tem falha transiente."""
    for attempt in (1, 2):
        result = subprocess.run(["gh", *args], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        print(
            f"gh {args[0]} falhou (rc={result.returncode}, tentativa {attempt}): "
            f"{result.stderr.strip()}",
            file=sys.stderr,
        )
        if attempt == 1:
            time.sleep(5)
    raise subprocess.CalledProcessError(
        result.returncode, result.args, result.stdout, result.stderr
    )


def list_open_prs() -> list[dict[str, Any]]:
    """Lista PRs abertos com os campos usados pela seleção do trem."""
    return json.loads(_gh("pr", "list", "--state", "open", "--json", PR_LIST_FIELDS))


def _has_excluded_label(pr: dict[str, Any]) -> bool:
    return any(label.get("name", "").lower() in EXCLUDED_LABELS for label in pr.get("labels") or [])


def required_check_failed(pr: dict[str, Any]) -> bool:
    """True se um required check do Ruleset está FAILURE genuíno no head atual —
    agregador FAILURE com sibling CANCELLED é run superseded (stale aggregator),
    não código vermelho: skipar causaria starvation (PR nunca ganha SHA novo
    que limpe o rollup)."""
    failed: set[str] = set()
    any_cancelled = False
    for check in pr.get("statusCheckRollup") or []:
        name = check.get("name") or check.get("context") or ""
        conclusion = check.get("conclusion") or check.get("state") or ""
        any_cancelled = any_cancelled or conclusion == "CANCELLED"
        if name in REQUIRED_CONTEXTS and conclusion == "FAILURE":
            failed.add(name)
    if "Title (Conventional Commits)" in failed:
        return True
    return "All checks green" in failed and not any_cancelled


def eligible_train(prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fila FIFO (createdAt asc) de PRs com auto-merge, sem draft/label de exclusão."""
    queue = [
        pr
        for pr in prs
        if pr.get("autoMergeRequest") and not pr.get("isDraft") and not _has_excluded_label(pr)
    ]
    return sorted(queue, key=lambda pr: pr["createdAt"])


def select_pr_to_update(prs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Primeiro PR BEHIND da fila cujo turno chegou; None se o trem deve esperar —
    DIRTY e required-check FAILURE saem do trem (não mergeiam de qualquer forma),
    e PENDING nunca é pulado: atualizar o próximo enquanto a cabeça roda CI
    desperdiça runs e pode livelock (ADR-322 §D1)."""
    for pr in eligible_train(prs):
        status = pr.get("mergeStateStatus")
        if status == "DIRTY":
            print(f"skip #{pr['number']}: conflito de merge — autor precisa rebasar")
            continue
        if required_check_failed(pr):
            print(f"skip #{pr['number']}: required check FAILURE no head atual")
            continue
        if status == "BEHIND":
            return pr
        print(f"hold #{pr['number']}: mergeStateStatus={status} — cabeça do trem em andamento")
        return None
    return None


def update_branch(number: int) -> None:
    """PUT update-branch: merge de main na branch do PR com a identidade do token."""
    _gh("api", "-X", "PUT", f"repos/{{owner}}/{{repo}}/pulls/{number}/update-branch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="só decide, não atualiza")
    args = parser.parse_args()
    pr = select_pr_to_update(list_open_prs())
    if pr is None:
        print("trem em dia: nenhum PR elegível BEHIND")
        return 0
    print(f"update-branch #{pr['number']} — {pr['title']}")
    if not args.dry_run:
        update_branch(pr["number"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
