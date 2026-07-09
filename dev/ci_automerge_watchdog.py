#!/usr/bin/env python3
"""Watchdog do trem de auto-merge (ADR-322): (a) re-habilita auto-merge derrubado
por agregador stale, (b) re-dispara CI órfão action_required via empty commit —
só com token de identidade real (AUTOMERGE_KICK=1), (c) mantém issue de
sinalização quando a cabeça trava >60min. Uso local: python3 dev/ci_automerge_watchdog.py [--dry-run]"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.ci_advance_automerge_train import (  # noqa: E402
    _gh,
    eligible_train,
    required_check_failed,
)

WATCHDOG_PR_FIELDS = (
    "number,title,createdAt,isDraft,labels,mergeStateStatus,"
    "autoMergeRequest,statusCheckRollup,headRefName,headRefOid"
)
STALL_MINUTES = 60
MAX_KICKS_PER_RUN = 3
STALL_ISSUE_TITLE = "CI: trem de auto-merge travado — ação necessária"
RUNBOOK = "docs/reference/runbooks/automerge_train.md"

AUTOMERGE_EVENT_QUERY = """
query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){ pullRequest(number:$number){
    timelineItems(last:1,itemTypes:[AUTO_MERGE_DISABLED_EVENT,AUTO_MERGE_ENABLED_EVENT]){
      nodes{ __typename }
    }
  } }
}
"""


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def list_watchdog_prs() -> list[dict[str, Any]]:
    return json.loads(_gh("pr", "list", "--state", "open", "--json", WATCHDOG_PR_FIELDS))


def runs_for_commit(sha: str) -> list[dict[str, Any]]:
    return json.loads(
        _gh(
            "run", "list", "--commit", sha, "--limit", "20", "--json", "status,conclusion,updatedAt"
        )
    )


def is_orphan_run_set(runs: list[dict[str, Any]]) -> bool:
    """True se o head só tem runs action_required — CI nunca vai rodar (bot push)."""
    return bool(runs) and all(r.get("conclusion") == "action_required" for r in runs)


def is_stalled(runs: list[dict[str, Any]], now: datetime) -> bool:
    """True se nada roda nem rodou recentemente no head da cabeça do trem."""
    if not runs:
        return True
    if any(r.get("status") != "completed" for r in runs):
        return False
    newest = max(_parse_ts(r["updatedAt"]) for r in runs)
    return now - newest > timedelta(minutes=STALL_MINUTES)


def aggregator_green(pr: dict[str, Any]) -> bool:
    for check in pr.get("statusCheckRollup") or []:
        name = check.get("name") or check.get("context") or ""
        if name == "All checks green":
            return (check.get("conclusion") or check.get("state")) == "SUCCESS"
    return False


def last_automerge_event(number: int) -> str | None:
    out = _gh(
        "api",
        "graphql",
        "-F",
        "owner={owner}",
        "-F",
        "name={repo}",
        "-F",
        f"number={number}",
        "-f",
        f"query={AUTOMERGE_EVENT_QUERY}",
    )
    nodes = json.loads(out)["data"]["repository"]["pullRequest"]["timelineItems"]["nodes"]
    return nodes[0]["__typename"] if nodes else None


def reenable_stale_disabled(prs: list[dict[str, Any]], dry_run: bool) -> None:
    """Re-liga auto-merge derrubado por agregador stale (run superseded); opt-out
    humano via label wip/do-not-merge/blocked — re-checada aqui porque o
    candidato não tem auto-merge e escapa de eligible_train."""
    for pr in prs:
        if pr.get("autoMergeRequest") or pr.get("isDraft"):
            continue
        labels = {label.get("name", "").lower() for label in pr.get("labels") or []}
        if labels & {"wip", "do-not-merge", "blocked"}:
            continue
        if not aggregator_green(pr) or pr.get("mergeStateStatus") == "DIRTY":
            continue
        if last_automerge_event(pr["number"]) != "AutoMergeDisabledEvent":
            continue
        print(f"re-enable auto-merge #{pr['number']}: head verde + disable automático detectado")
        if not dry_run:
            _gh("pr", "merge", str(pr["number"]), "--squash", "--auto")


def _create_empty_commit(oid: str) -> str:
    """Commit vazio sobre oid via Git Data API; retorna o novo SHA."""
    tree = _gh("api", f"repos/{{owner}}/{{repo}}/git/commits/{oid}", "--jq", ".tree.sha").strip()
    args = [
        "api", "-X", "POST", "repos/{owner}/{repo}/git/commits",
        "-f", "message=chore(ci): kick — re-dispara CI de runs action_required órfãos (ADR-322)",
        "-f", f"tree={tree}",
        "-f", f"parents[]={oid}",
        "--jq", ".sha",
    ]  # fmt: skip
    return _gh(*args).strip()


def kick_orphan(pr: dict[str, Any], dry_run: bool) -> None:
    """Empty commit via Git Data API — novo SHA re-dispara CI com a identidade do token."""
    oid, branch = pr["headRefOid"], pr["headRefName"]
    print(f"kick #{pr['number']}: runs órfãos action_required em {oid[:8]} ({branch})")
    if dry_run:
        return
    new_sha = _create_empty_commit(oid)
    _gh(
        "api",
        "-X",
        "PATCH",
        f"repos/{{owner}}/{{repo}}/git/refs/heads/{branch}",
        "-f",
        f"sha={new_sha}",
    )


def kick_orphans(prs: list[dict[str, Any]], dry_run: bool) -> None:
    if os.environ.get("AUTOMERGE_KICK") != "1":
        print("kick desabilitado: sem AUTOUPDATE_PAT (push do GITHUB_TOKEN geraria novo órfão)")
        return
    kicked = 0
    for pr in eligible_train(prs):
        if kicked >= MAX_KICKS_PER_RUN:
            return
        if is_orphan_run_set(runs_for_commit(pr["headRefOid"])):
            kick_orphan(pr, dry_run)
            kicked += 1


def train_head(prs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Cabeça efetiva do trem: primeiro elegível que não está fora (DIRTY/red)."""
    for pr in eligible_train(prs):
        if pr.get("mergeStateStatus") == "DIRTY" or required_check_failed(pr):
            continue
        return pr
    return None


def _find_stall_issue() -> int | None:
    out = _gh(
        "issue",
        "list",
        "--state",
        "open",
        "--search",
        f'in:title "{STALL_ISSUE_TITLE}"',
        "--json",
        "number",
    )
    issues = json.loads(out)
    return issues[0]["number"] if issues else None


def _stall_body(pr: dict[str, Any]) -> str:
    return (
        f"A cabeça do trem de auto-merge — PR #{pr['number']} "
        f"({pr.get('mergeStateStatus')}) — está sem progresso há mais de "
        f"{STALL_MINUTES}min (nenhum run ativo no head `{pr['headRefOid'][:8]}`).\n\n"
        f"Causas prováveis: `AUTOUPDATE_PAT` ausente/expirado, budget de Actions "
        f"esgotado, ou run órfão `action_required`.\n\n"
        f"Diagnóstico e ações: `{RUNBOOK}`.\n\n"
        f"_Issue mantida pelo watchdog (`dev/ci_automerge_watchdog.py`); "
        f"fecha sozinha quando o trem anda._"
    )


def _upsert_stall_issue(head: dict[str, Any], issue: int | None, dry_run: bool) -> None:
    print(f"stall: cabeça #{head['number']} parada >{STALL_MINUTES}min")
    if dry_run:
        return
    if issue is None:
        _gh("issue", "create", "--title", STALL_ISSUE_TITLE, "--body", _stall_body(head))
    else:
        _gh("issue", "edit", str(issue), "--body", _stall_body(head))


def _close_stall_issue(issue: int, dry_run: bool) -> None:
    print(f"trem andou — fechando issue #{issue}")
    if dry_run:
        return
    _gh("issue", "close", str(issue), "--comment", "Trem de auto-merge voltou a andar.")


def signal_stall(prs: list[dict[str, Any]], dry_run: bool) -> None:
    head = train_head(prs)
    now = datetime.now(timezone.utc)
    stalled = head is not None and is_stalled(runs_for_commit(head["headRefOid"]), now)
    issue = _find_stall_issue()
    if stalled and head is not None:
        _upsert_stall_issue(head, issue, dry_run)
    elif issue is not None:
        _close_stall_issue(issue, dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="só reporta, não age")
    args = parser.parse_args()
    prs = list_watchdog_prs()
    reenable_stale_disabled(prs, args.dry_run)
    kick_orphans(prs, args.dry_run)
    signal_stall(prs, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
