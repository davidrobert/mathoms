#!/usr/bin/env python3
"""Avança o trem de auto-merge (ADR-322): update-branch em exatamente 1 PR por
invocação. Uso local (identidade do `gh auth`): python3 dev/ci_advance_automerge_train.py [--dry-run]"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable

EXCLUDED_LABELS = {"wip", "do-not-merge", "blocked"}
# Workflows que hospedam os required checks do Ruleset: job "All checks
# green" vive no workflow CI; job "Title (Conventional Commits)" no PR
# Quality. Estado lido via API de Actions (escopo Actions:Read) porque
# fine-grained PAT não acessa check-runs do statusCheckRollup (GraphQL).
REQUIRED_WORKFLOWS = {"CI", "PR Quality"}
PR_LIST_FIELDS = (
    "number,title,createdAt,isDraft,labels,mergeStateStatus,autoMergeRequest,headRefOid"
)

RunsFetcher = Callable[[dict[str, Any]], list[dict[str, Any]]]


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


def runs_for_commit(sha: str) -> list[dict[str, Any]]:
    """Runs de workflow no SHA, do mais novo ao mais velho (ordem do gh run list)."""
    return json.loads(
        _gh(
            "run",
            "list",
            "--commit",
            sha,
            "--limit",
            "20",
            "--json",
            "name,status,conclusion,updatedAt",
        )  # fmt: skip
    )


def _runs_for_pr(pr: dict[str, Any]) -> list[dict[str, Any]]:
    return runs_for_commit(pr["headRefOid"])


def _has_excluded_label(pr: dict[str, Any]) -> bool:
    return any(label.get("name", "").lower() in EXCLUDED_LABELS for label in pr.get("labels") or [])


def latest_required_runs(runs: list[dict[str, Any]]) -> dict[str, tuple[str, str]]:
    """(status, conclusion) do run mais recente de cada workflow required."""
    latest: dict[str, tuple[str, str]] = {}
    for run in runs:
        name = run.get("name") or ""
        if name in REQUIRED_WORKFLOWS and name not in latest:
            latest[name] = (run.get("status") or "", run.get("conclusion") or "")
    return latest


def required_workflow_failed(runs: list[dict[str, Any]]) -> bool:
    """True se o run mais recente de um workflow required concluiu failure —
    cancelled é supersede (stale aggregator), não código vermelho: skipar
    causaria starvation (PR nunca ganha SHA novo que limpe o estado)."""
    return any(
        status == "completed" and conclusion == "failure"
        for status, conclusion in latest_required_runs(runs).values()
    )


def required_workflows_green(runs: list[dict[str, Any]]) -> bool:
    """True se os runs mais recentes de TODOS os workflows required concluíram success."""
    latest = latest_required_runs(runs)
    return len(latest) == len(REQUIRED_WORKFLOWS) and all(
        status == "completed" and conclusion == "success" for status, conclusion in latest.values()
    )


def eligible_train(prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fila FIFO (createdAt asc) de PRs com auto-merge, sem draft/label de exclusão."""
    queue = [
        pr
        for pr in prs
        if pr.get("autoMergeRequest") and not pr.get("isDraft") and not _has_excluded_label(pr)
    ]
    return sorted(queue, key=lambda pr: pr["createdAt"])


@dataclass(frozen=True)
class TrainDecision:
    """Resultado de um ciclo: o PR a atualizar, ou por que não há um. `waiting_behind`
    conta elegíveis em BEHIND atrás da cabeça — mesmo predicado do `gh pr list` do
    runbook §1, não promessa de que todos sejam atualizáveis (um deles pode estar
    red no head e sair do trem quando chegar a vez dele)."""

    pr: dict[str, Any] | None
    head_on_hold: dict[str, Any] | None
    waiting_behind: int


def _behind_in(prs: list[dict[str, Any]]) -> int:
    return sum(1 for pr in prs if pr.get("mergeStateStatus") == "BEHIND")


def decide_train(prs: list[dict[str, Any]], runs_for: RunsFetcher = _runs_for_pr) -> TrainDecision:
    """Primeiro PR BEHIND da fila cujo turno chegou, ou o motivo de o trem esperar —
    DIRTY e workflow required em failure saem do trem (não mergeiam de qualquer
    forma), e PENDING nunca é pulado: atualizar o próximo enquanto a cabeça
    roda CI desperdiça runs e pode livelock (ADR-322 §D1). Fila vazia e cabeça
    segurando são estados distintos: nenhum dos dois atualiza PR, mas só o
    segundo tem trabalho em voo e fila atrás."""
    queue = eligible_train(prs)
    for position, pr in enumerate(queue):
        status = pr.get("mergeStateStatus")
        if status == "DIRTY":
            print(f"skip #{pr['number']}: conflito de merge — autor precisa rebasar")
            continue
        if required_workflow_failed(runs_for(pr)):
            print(f"skip #{pr['number']}: workflow required em failure no head atual")
            continue
        if status == "BEHIND":
            return TrainDecision(pr, None, 0)
        return TrainDecision(None, pr, _behind_in(queue[position + 1 :]))
    return TrainDecision(None, None, 0)


def select_pr_to_update(
    prs: list[dict[str, Any]], runs_for: RunsFetcher = _runs_for_pr
) -> dict[str, Any] | None:
    """PR que o trem atualiza neste ciclo; o motivo de um None vive em decide_train."""
    return decide_train(prs, runs_for).pr


def update_branch(number: int) -> None:
    """PUT update-branch: merge de main na branch do PR com a identidade do token."""
    _gh("api", "-X", "PUT", f"repos/{{owner}}/{{repo}}/pulls/{number}/update-branch")


def describe_decision(decision: TrainDecision) -> str:
    """Linha final do run. Fila vazia e cabeça segurando tiveram a mesma frase até
    2026-08-21 ("trem em dia") — ela afirmava zero elegível BEHIND com 5 esperando
    atrás do #1569, e fez enfileiramento saudável parecer trem parado."""
    if decision.pr is not None:
        return f"update-branch #{decision.pr['number']} — {decision.pr['title']}"
    head = decision.head_on_hold
    if head is None:
        return "trem em dia: nenhum PR elegível BEHIND"
    atras = (
        f"{decision.waiting_behind} PR(s) elegível(is) BEHIND atrás"
        if decision.waiting_behind
        else "nenhum PR elegível atrás"
    )
    return (
        f"trem segurando: cabeça #{head['number']} em andamento "
        f"(mergeStateStatus={head.get('mergeStateStatus')}) — {atras}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="só decide, não atualiza")
    args = parser.parse_args()
    decision = decide_train(list_open_prs())
    print(describe_decision(decision))
    if decision.pr is not None and not args.dry_run:
        update_branch(decision.pr["number"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
