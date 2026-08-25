#!/usr/bin/env python3
"""Avança o trem de auto-merge (ADR-322): update-branch em exatamente 1 PR por
invocação. Uso local (identidade do `gh auth`): python3 dev/ci_advance_automerge_train.py [--dry-run]"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from typing import Any, Callable

EXCLUDED_LABELS = {"wip", "do-not-merge", "blocked"}
# Recusas toleradas por ciclo. Quando o merge de main traz mudança em
# `.github/workflows/**`, TODOS os PRs BEHIND recusam pela mesma causa —
# varrer a fila inteira gasta chamadas sem mudar desfecho, e o run seguinte
# (~15min) tenta de novo. Três dá amostra para o operador ver que é sistêmico.
MAX_REFUSALS_PER_RUN = 3
# Workflows que hospedam os required checks do Ruleset: job "All checks
# green" vive no workflow CI; job "Title (Conventional Commits)" no PR
# Quality. Estado lido via API de Actions (escopo Actions:Read) porque
# fine-grained PAT não acessa check-runs do statusCheckRollup (GraphQL).
REQUIRED_WORKFLOWS = {"CI", "PR Quality"}
PR_LIST_FIELDS = (
    "number,title,createdAt,isDraft,labels,mergeStateStatus,autoMergeRequest,headRefOid"
)

RunsFetcher = Callable[[dict[str, Any]], list[dict[str, Any]]]
_HTTP_STATUS_RE = re.compile(r"HTTP (\d{3})")
_RATE_LIMIT_RE = re.compile(r"rate limit|abuse detection|secondary", re.IGNORECASE)


class GhCallFailed(RuntimeError):
    """Falha de `gh` com o status HTTP preservado. A classe do erro decide o
    desfecho: 4xx é veredito da API (permissão, escopo, estado do PR) e repetir
    só gasta relógio; 5xx é indisponibilidade e pode ceder. Medido em
    2026-08-17: o retry cego re-tentou 9× um 403 de escopo de PAT e recuperou
    0 de 10 ([[ADR-210]] §Adendo 2026-08-21c)."""

    def __init__(self, returncode: int, stderr: str) -> None:
        self.returncode = returncode
        self.stderr = stderr
        found = _HTTP_STATUS_RE.search(stderr)
        self.status = int(found.group(1)) if found else None
        super().__init__(self.describe())

    @property
    def is_rate_limited(self) -> bool:
        """429, e o 403 que o GitHub usa para rate limit secundário — 4xx pelo
        número, transiente pelo mecanismo. A medição que motivou o corte por
        classe (0 de 10 recuperados) é sobre 403 de ESCOPO de PAT; tratar a
        faixa 4xx inteira como definitiva estenderia a conclusão a uma classe
        que ela não mediu, e retry é justamente o remédio desta."""
        if self.status == 429:
            return True
        return self.status == 403 and bool(_RATE_LIMIT_RE.search(self.stderr))

    @property
    def is_verdict(self) -> bool:
        """True quando a API respondeu recusando (4xx) — re-tentar não muda."""
        if self.is_rate_limited:
            return False
        return self.status is not None and 400 <= self.status < 500

    def describe(self) -> str:
        head = f"HTTP {self.status}" if self.status else f"rc={self.returncode}"
        first_line = self.stderr.strip().splitlines()[0] if self.stderr.strip() else ""
        return f"{head}: {first_line[:140]}" if first_line else head


def _gh(*args: str) -> str:
    """gh CLI com 1 retry (backoff 5s) reservado a falha NÃO-determinística —
    4xx sai na primeira tentativa, com a causa na exceção."""
    failure = GhCallFailed(-1, "nenhuma tentativa executada")
    for attempt in (1, 2):
        result = subprocess.run(["gh", *args], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        failure = GhCallFailed(result.returncode, result.stderr)
        print(f"gh {args[0]} falhou (tentativa {attempt}): {failure.describe()}", file=sys.stderr)
        if failure.is_verdict:
            break
        if attempt == 1:
            time.sleep(5)
    raise failure


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


def out_of_train_reason(pr: dict[str, Any], runs_for: RunsFetcher) -> str | None:
    """Motivo de o PR estar fora do trem, ou None se ele concorre à cabeça — fonte
    única da exclusão. `decide_train` e o `train_head` do watchdog diferem no
    desfecho (um para na cabeça, o outro a devolve mesmo sem BEHIND) e precisam
    concordar sobre QUEM ela é: motivo novo aqui vale para os dois. `runs_for` é
    lazy — PR DIRTY sai sem gastar chamada de API. A recusa 403 do update-branch
    **não** entra aqui (versão anterior deste texto a previa): não é propriedade
    do PR e sim de uma tentativa, invisível ao watchdog, que compartilha este
    predicado — ela vive em `advance_train` (ADR-322 §Emenda 2026-08-25)."""
    if pr.get("mergeStateStatus") == "DIRTY":
        return "conflito de merge — autor precisa rebasar"
    if required_workflow_failed(runs_for(pr)):
        return "workflow required em failure no head atual"
    return None


@dataclass(frozen=True)
class Refusal:
    """PR cujo update-branch a API recusou, com a causa OBSERVADA. Guardar só o
    número obrigaria a linha final a supor o motivo — e ela supunha 403."""

    number: int
    status: int | None
    detail: str


@dataclass(frozen=True)
class TrainDecision:
    """Resultado de um ciclo: o PR a atualizar, ou por que não há um. `waiting_behind`
    conta elegíveis em BEHIND atrás da cabeça — mesmo predicado do `gh pr list` do
    runbook §1, não promessa de que todos sejam atualizáveis (um deles pode estar
    red no head e sair do trem quando chegar a vez dele). `refused` lista os PRs
    cujo update-branch a API recusou neste ciclo: eles não são fila em andamento
    nem fila vazia, e a linha final precisa dizer isso — foi "trem em dia"
    afirmado sobre 5 PRs esperando que custou 22min de diagnóstico em 08-21."""

    pr: dict[str, Any] | None
    head_on_hold: dict[str, Any] | None
    waiting_behind: int
    refused: tuple[Refusal, ...] = ()

    @property
    def hit_refusal_cap(self) -> bool:
        """Ciclo interrompido pelo teto: sobrou fila não tentada."""
        return len(self.refused) >= MAX_REFUSALS_PER_RUN


def _behind_in(prs: list[dict[str, Any]]) -> int:
    return sum(1 for pr in prs if pr.get("mergeStateStatus") == "BEHIND")


def decide_train(prs: list[dict[str, Any]], runs_for: RunsFetcher = _runs_for_pr) -> TrainDecision:
    """Primeiro PR BEHIND da fila cujo turno chegou, ou o motivo de o trem esperar —
    quem out_of_train_reason exclui é pulado, e PENDING nunca é pulado: atualizar
    o próximo enquanto a cabeça roda CI desperdiça runs e pode livelock
    (ADR-322 §D1). Fila vazia e cabeça segurando são estados distintos: nenhum
    dos dois atualiza PR, mas só o segundo tem trabalho em voo e fila atrás."""
    queue = eligible_train(prs)
    for position, pr in enumerate(queue):
        reason = out_of_train_reason(pr, runs_for)
        if reason is not None:
            print(f"skip #{pr['number']}: {reason}")
            continue
        if pr.get("mergeStateStatus") == "BEHIND":
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


def _attempt_update(number: int, updater: Callable[[int], None]) -> Refusal | None:
    """A recusa (4xx que não seja rate limit), ou None se o update passou. 5xx e
    rate limit sobem: indisponibilidade não é veredito sobre este PR, e engolir
    viraria skip de um PR que estava são."""
    try:
        updater(number)
    except GhCallFailed as failure:
        if not failure.is_verdict:
            raise
        print(f"skip #{number}: update-branch recusado — {failure.describe()}")
        return Refusal(number, failure.status, failure.describe())
    return None


def _refusal_cause(refused: tuple[Refusal, ...]) -> str:
    """A causa que o operador lê sai do STATUS observado. Afirmar "403 é PAT sem
    escopo workflow" para um 404/422 seria inventar diagnóstico — e a própria
    ADR-322 §Emenda 2026-08-25 registra que o mecanismo do 403 continua em
    disputa, então nem para o 403 a frase pode fechar a questão."""
    if all(r.status == 403 for r in refused):
        return (
            "403 costuma ser PAT sem escopo `workflow` diante de merge que toca "
            ".github/workflows/** — nesse caso o autor rebasa da própria conta "
            "(ADR-322 §Emenda 2026-08-08)"
        )
    return "; ".join(f"#{r.number}: {r.detail}" for r in refused)


def advance_train(
    prs: list[dict[str, Any]],
    runs_for: RunsFetcher = _runs_for_pr,
    updater: Callable[[int], None] | None = None,
) -> TrainDecision:
    """Decide, atualiza, e tenta o PRÓXIMO quando a API recusa — o 403 é terminal
    para aquele PR e nunca para o run (ADR-322 §Emenda 2026-08-25)."""
    # `updater=None` resolvido no corpo: default de assinatura ligaria o símbolo
    # na definição, e o monkeypatch do teste chamaria a API de verdade.
    apply_update = updater or update_branch
    candidates: list[dict[str, Any]] = list(prs)
    refused: list[Refusal] = []
    while len(refused) < MAX_REFUSALS_PER_RUN:
        decision = decide_train(candidates, runs_for)
        recusa = _cycle_outcome(decision, apply_update)
        if recusa is None:
            return replace(decision, refused=tuple(refused))
        refused.append(recusa)
        candidates = [pr for pr in candidates if pr["number"] != recusa.number]
    return TrainDecision(None, None, 0, tuple(refused))


def _cycle_outcome(decision: TrainDecision, apply_update: Callable[[int], None]) -> Refusal | None:
    """Recusa a registrar, ou None quando o ciclo termina (nada a atualizar, ou
    update aceito) — os dois desfechos que encerram `advance_train`."""
    if decision.pr is None:
        return None
    return _attempt_update(decision.pr["number"], apply_update)


def _no_head_phrase(decision: TrainDecision) -> str:
    """Teto de recusas e fila esgotada NÃO compartilham frase. Foi dizer "trem
    em dia" sobre 5 PRs esperando que custou 22min de diagnóstico em 08-21; um
    teto que se disfarça de fila vazia é a mesma classe, com outro nome."""
    if decision.hit_refusal_cap:
        return (
            f"teto de {MAX_REFUSALS_PER_RUN} recusas atingido — a fila NÃO foi "
            "esgotada; os demais PRs não chegaram a ser tentados neste ciclo"
        )
    return "nada mais a atualizar" if decision.refused else "trem em dia: nenhum PR elegível BEHIND"


def _refused_phrase(refused: tuple[Refusal, ...]) -> str:
    listed = ", ".join(f"#{r.number}" for r in refused)
    return f"{len(refused)} update-branch recusado(s) em {listed} — {_refusal_cause(refused)}"


def _outcome_phrase(decision: TrainDecision) -> str:
    if decision.pr is not None:
        return f"update-branch #{decision.pr['number']} — {decision.pr['title']}"
    head = decision.head_on_hold
    if head is None:
        return _no_head_phrase(decision)
    atras = (
        f"{decision.waiting_behind} PR(s) elegível(is) BEHIND atrás"
        if decision.waiting_behind
        else "nenhum PR elegível atrás"
    )
    return (
        f"trem segurando: cabeça #{head['number']} em andamento "
        f"(mergeStateStatus={head.get('mergeStateStatus')}) — {atras}"
    )


def describe_decision(decision: TrainDecision) -> str:
    """Linha final do run. Fila vazia e cabeça segurando tiveram a mesma frase até
    2026-08-21 ("trem em dia") — ela afirmava zero elegível BEHIND com 5 esperando
    atrás do #1569, e fez enfileiramento saudável parecer trem parado. Recusa é o
    terceiro estado: dizer "trem em dia" depois de recusar 3 updates recriaria
    exatamente aquele defeito."""
    parts = [_refused_phrase(decision.refused)] if decision.refused else []
    parts.append(_outcome_phrase(decision))
    return " · ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="só decide, não atualiza")
    args = parser.parse_args()
    prs = list_open_prs()
    decision = decide_train(prs) if args.dry_run else advance_train(prs)
    print(describe_decision(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
