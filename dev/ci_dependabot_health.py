#!/usr/bin/env python3
"""Saúde das entradas do Dependabot: mantém UMA issue rotulada quando uma entrada de
`.github/dependabot.yml` fica vermelha (2 últimas runs `failure`), sem run além do
intervalo, ou com PR parado ocupando vaga. Falha da medição vira warning, nunca run vermelho.
Uso: python3 dev/ci_dependabot_health.py --label X [--dry-run]

Limite declarado: o aviso "cannot open any more pull requests" só aparece na UI do
Dependabot (`network/updates`). A ocupação de vagas aqui é contada pelos PRs abertos,
com security update junto — ela aproxima o aviso, não o lê."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.ci_advance_automerge_train import _gh  # noqa: E402
from dev.ci_dependabot_stuck_prs import (  # noqa: E402
    DependabotPr,
    Occupancy,
    StuckPr,
    fetch_dependabot_prs,
    parse_pr,
    stuck_prs,
)

CONFIG = REPO_ROOT / ".github/dependabot.yml"
WORKFLOW_PATH = "dynamic/dependabot/dependabot-updates"
LOOKBACK_DAYS = 90
STALE_LIMIT = {
    "daily": timedelta(days=3),
    "weekly": timedelta(days=10),
    "monthly": timedelta(days=40),
}
DEFAULT_LIMIT = STALE_LIMIT["weekly"]
# Co-design sre-devops 2026-10-09: o cron roda 02:00 UTC e o Dependabot segunda 09:00
# UTC. PR da run cruza 5 dias no sábado e o cron avisa domingo, ANTES da run seguinte;
# com 7 o aviso chegaria depois dela por construção. PR saudável mergeia em ≤1,3 dia.
STUCK_PR_AGE = timedelta(days=5)
DEFAULT_PR_LIMIT = 5
# Medido em 2026-10-09 sobre as 395 runs `event=dynamic` do workflow 261301753: o
# título usa o nome interno do ecossistema e a raiz vira `/.` (`pip in /. - Update #N`).
# `go_modules` só foi observado em título de security update; não há entrada gomod.
TITLE_ECOSYSTEM = {
    "pip": "pip",
    "npm": "npm_and_yarn",
    "docker": "docker",
    "github-actions": "github_actions",
    "gomod": "go_modules",
}
# Rebase/security update de PR traz ` for <deps>` antes do ` - Update` e não casa.
SCHEDULED_TITLE = re.compile(r"^(?P<key>\S+ in \S+) - Update #\d+$")
RUN_FIELDS = ".workflow_runs[] | {created_at, status, conclusion, display_title, html_url}"
ISSUE_TITLE = "Dependabot: entrada vermelha, sem run ou com PR parado"
TABLE_ROW = re.compile(r"^\| `(?P<entry>[^`]+)` \| (?P<signal>[^|]+?) \|", re.MULTILINE)
RUNBOOK = "docs/reference/runbooks/python_dependencies.md"


@dataclass(frozen=True)
class DependabotEntry:
    ecosystem: str
    directory: str | None
    interval: str
    pr_limit: int = DEFAULT_PR_LIMIT

    @property
    def name(self) -> str:
        return f"{self.ecosystem} {self.directory or '(directories)'}"

    def title_key(self) -> str | None:
        """`<eco> in <dir>` como o título da run agendada o grafa, ou None se não medido."""
        eco = TITLE_ECOSYSTEM.get(self.ecosystem)
        if eco is None or self.directory is None:
            return None
        return f"{eco} in {self.directory.rstrip('/') or '/.'}"

    def branch_key(self) -> tuple[str, str | None]:
        """(ecossistema, diretório) como a branch `dependabot/…` do PR os grafa."""
        return TITLE_ECOSYSTEM.get(self.ecosystem, self.ecosystem), self.directory


@dataclass(frozen=True)
class UpdateRun:
    key: str
    created_at: datetime
    status: str
    conclusion: str | None
    url: str

    def link(self) -> str:
        return f"[{self.created_at:%Y-%m-%d}]({self.url})"


@dataclass(frozen=True)
class EntryFinding:
    entry: str
    signal: str
    evidence: str
    newest_fact: datetime | None = None
    limit: timedelta = DEFAULT_LIMIT
    occupancy: Occupancy | None = None

    def is_new_since(self, closed_at: datetime | None, now: datetime) -> bool:
        """Fechar à mão é triagem: só reabre com fato posterior ao fechamento."""
        if closed_at is None:
            return True
        if self.occupancy is not None and self.occupancy.filled_since(closed_at):
            return True
        if self.newest_fact is not None:
            return self.newest_fact > closed_at
        return now - closed_at > self.limit


@dataclass(frozen=True)
class Triage:
    """Último fechamento da issue: achado sem fato posterior a ele já foi triado."""

    closed_at: datetime | None
    now: datetime

    def is_fresh(self, finding: EntryFinding) -> bool:
        return finding.is_new_since(self.closed_at, self.now)

    def mark(self, finding: EntryFinding) -> str:
        if self.closed_at is None or self.is_fresh(finding):
            return ""
        return f" _(triado em {self.closed_at:%Y-%m-%d})_"


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_entries(path: Path = CONFIG) -> list[DependabotEntry]:
    import yaml

    updates = yaml.safe_load(path.read_text(encoding="utf-8"))["updates"]
    return [
        DependabotEntry(
            u["package-ecosystem"],
            u.get("directory"),
            u["schedule"]["interval"],
            u.get("open-pull-requests-limit", DEFAULT_PR_LIMIT),
        )
        for u in updates
    ]


def scheduled_runs(raw_runs: list[dict]) -> list[UpdateRun]:
    """Só as runs de entrada agendada, da mais nova para a mais velha."""
    runs = []
    for run in raw_runs:
        match = SCHEDULED_TITLE.match(run.get("display_title") or "")
        if match:
            runs.append(_update_run(match["key"], run))
    return sorted(runs, key=lambda r: r.created_at, reverse=True)


def _update_run(key: str, run: dict) -> UpdateRun:
    return UpdateRun(
        key, parse_ts(run["created_at"]), run["status"], run.get("conclusion"), run["html_url"]
    )


def red_finding(entry: DependabotEntry, runs: list[UpdateRun]) -> EntryFinding | None:
    """Vermelho = as 2 últimas concluídas `failure`; 1 isolada pode ser o registry."""
    last_two = [r for r in runs if r.status == "completed"][:2]
    if len(last_two) < 2 or any(r.conclusion != "failure" for r in last_two):
        return None
    links = ", ".join(r.link() for r in last_two)
    evidence = f"2 últimas runs concluídas `failure`: {links}"
    return EntryFinding(entry.name, "vermelho", evidence, newest_fact=last_two[0].created_at)


def stale_finding(
    entry: DependabotEntry, key: str, runs: list[UpdateRun], now: datetime
) -> EntryFinding | None:
    limit = STALE_LIMIT.get(entry.interval)
    if limit is None:
        evidence = f"`schedule.interval: {entry.interval}` sem limite em `STALE_LIMIT`"
        return EntryFinding(entry.name, "sem correspondência", evidence)
    if not runs:
        evidence = f"nenhuma run `{key} - Update #N` em {LOOKBACK_DAYS} dias"
        return EntryFinding(entry.name, "sem correspondência", evidence, limit=limit)
    last = runs[0]
    if now - last.created_at <= limit:
        return None
    outcome = last.conclusion or last.status
    evidence = f"última run {last.link()} (`{outcome}`); limite `{entry.interval}` = {limit.days}d"
    return EntryFinding(entry.name, "sem run", evidence, limit=limit)


def entry_findings(
    entry: DependabotEntry, runs: list[UpdateRun], now: datetime
) -> list[EntryFinding]:
    key = entry.title_key()
    if key is None:
        evidence = f"`{entry.ecosystem}` sem título medido em `TITLE_ECOSYSTEM`, ou `directories`"
        return [EntryFinding(entry.name, "sem correspondência", evidence)]
    mine = [r for r in runs if r.key == key]
    found = (red_finding(entry, mine), stale_finding(entry, key, mine, now))
    return [f for f in found if f is not None]


def measure_findings(
    entries: list[DependabotEntry], runs: list[UpdateRun], now: datetime
) -> list[EntryFinding]:
    return [f for entry in entries for f in entry_findings(entry, runs, now)]


def parse_prs(entries: list[DependabotEntry], raw_prs: list[dict]) -> list[DependabotPr]:
    dirs: dict[str, list[str]] = {}
    for entry in entries:
        eco, directory = entry.branch_key()
        if directory is not None:
            dirs.setdefault(eco, []).append(directory)
    return [parse_pr(raw, dirs) for raw in raw_prs]


def stuck_findings(
    entries: list[DependabotEntry], prs: list[DependabotPr], now: datetime
) -> list[EntryFinding]:
    """PR parado sem entrada no yml (só security, ex.: go_modules) também vira linha."""
    by_key = {entry.branch_key(): entry for entry in entries}
    groups: dict[tuple[str, str | None], list[StuckPr]] = {}
    for stuck in stuck_prs(prs, now, STUCK_PR_AGE):
        groups.setdefault(stuck.pr.entry_key(), []).append(stuck)
    return [_stuck_finding(by_key.get(k), k, group, prs) for k, group in groups.items()]


def _stuck_finding(
    entry: DependabotEntry | None,
    key: tuple[str, str | None],
    group: list[StuckPr],
    prs: list[DependabotPr],
) -> EntryFinding:
    links = "; ".join(f"[#{s.pr.number}]({s.pr.url}) `{s.pr.key}` desde {s.since:%Y-%m-%d}"
                      for s in group)  # fmt: skip
    newest = max(s.since for s in group) + STUCK_PR_AGE
    if entry is None:
        evidence = f"{links} · sem entrada no `dependabot.yml`: vagas n/d (só security)"
        return EntryFinding(f"{key[0]} (sem entrada)", "PR parado", evidence, newest_fact=newest)
    seats = Occupancy(entry.pr_limit, tuple(p for p in prs if p.entry_key() == key))
    evidence = f"{links} · {_seats(seats)}"
    return EntryFinding(entry.name, "PR parado", evidence, newest_fact=newest, occupancy=seats)


def _seats(occupancy: Occupancy) -> str:
    taken = f"{occupancy.open_now()}/{occupancy.limit} vagas ocupadas (security conta junto)"
    full = occupancy.open_now() >= occupancy.limit
    return f"**lotada**, {taken}: version updates travados" if full else taken


def _workflow_id(repo: str) -> str:
    query = f'.workflows[] | select(.path == "{WORKFLOW_PATH}") | .id'
    found = _gh("api", f"repos/{repo}/actions/workflows?per_page=100", "--jq", query).strip()
    if not found:
        raise ValueError(f"{WORKFLOW_PATH} ausente de actions/workflows — Dependabot desligado?")
    return found


def fetch_runs(repo: str, now: datetime) -> list[dict]:
    """Zero runs na janela é instrumento cego (token sem leitura), não 'tudo sem run'."""
    since = f"{now - timedelta(days=LOOKBACK_DAYS):%Y-%m-%d}"
    url = (
        f"repos/{repo}/actions/workflows/{_workflow_id(repo)}/runs"
        f"?event=dynamic&per_page=100&created=>={since}"
    )
    raw = _gh("api", "--paginate", url, "--jq", RUN_FIELDS)
    runs = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not runs:
        raise ValueError(f"0 runs event=dynamic desde {since} — o token lê {WORKFLOW_PATH}?")
    return runs


def issue_body(findings: list[EntryFinding], repo: str, triage: Triage | None = None) -> str:
    """Sem data de medição: corpo determinístico não é reeditado a cada run."""
    marks = [triage.mark(f) if triage else "" for f in findings]
    rows = "\n".join(
        f"| `{f.entry}` | {f.signal} | {f.evidence}{mark} |" for f, mark in zip(findings, marks)
    )
    return (
        f"Entradas de `.github/dependabot.yml` com problema:\n\n"
        f"| Entrada | Sinal | Evidência |\n|---|---|---|\n{rows}\n\n{triage_guide(repo)}"
    )


def triage_guide(repo: str) -> str:
    return (
        f"## Como triar\n\n"
        f"- **vermelho:** `gh run view <id> --log` na run citada; conserte em PR.\n"
        f"- **sem run / sem correspondência:** em https://github.com/{repo}/network/updates, "
        f"*Check for updates* na entrada. Entrada que nunca completou job deixa de ser agendada.\n"
        f"- **PR parado** (cadeia de substituição aberta há mais de {STUCK_PR_AGE.days} dias): "
        f"merge (pip: regenere o `.lock`), lane de migração, ou `ignore` datado no "
        f"`dependabot.yml` e só então feche o PR. Nunca só fechar o PR nem `@dependabot ignore`: "
        f"os dois viram ignore fora do git. Deixar aberto com vaga sobrando é triagem válida.\n"
        f"- **Feche esta issue à mão**, com comentário apontando o PR do conserto. Não espere "
        f"a próxima run passar: o `S3` (10 dias) reprova o `Lint` do próprio PR do conserto.\n"
        f"- O cron só abre issue nova com fato posterior ao fechamento: run `failure` criada "
        f'depois dele, o limite de "sem run" vencido de novo, PR cruzando '
        f"{STUCK_PR_AGE.days} dias, ou a entrada do PR deixado aberto lotar.\n\n"
        f'Limite: "cannot open any more pull requests" só aparece na UI do Dependabot; a '
        f"ocupação acima conta os PRs abertos, com security update junto.\n\n"
        f"Runbook: `{RUNBOOK}` §Saúde das entradas do Dependabot.\n\n"
        f"_Mantida por `dev/ci_dependabot_health.py`; `S3` de 10 dias no manifesto._"
    )


def labelled_issues(label: str) -> list[dict]:
    fields = "number,state,body,closedAt"
    out = _gh(
        "issue", "list", "--state", "all", "--label", label, "--limit", "20", "--json", fields
    )
    return json.loads(out)


def last_closed_at(issues: list[dict]) -> datetime | None:
    closed = [parse_ts(i["closedAt"]) for i in issues if i.get("closedAt")]
    return max(closed) if closed else None


def close_comment(previous_body: str, findings: list[EntryFinding]) -> str:
    """Diz qual sinal zerou: o fechamento automático também vira `closed_at` de triagem."""
    still = {(f.entry, f.signal) for f in findings}
    rows = TABLE_ROW.finditer(previous_body)
    gone = [
        f"`{m['entry']}` ({m['signal']})" for m in rows if (m["entry"], m["signal"]) not in still
    ]
    rest = "Restam só achados já triados." if findings else "Todas as entradas saudáveis."
    return f"Zerou: {', '.join(gone)}. {rest}" if gone else rest


def refresh_open(
    issue: dict, findings: list[EntryFinding], triage: Triage, repo: str, dry_run: bool
) -> None:
    number = str(issue["number"])
    if not any(triage.is_fresh(f) for f in findings):
        comment = close_comment(issue.get("body") or "", findings)
        if not dry_run:
            _gh("issue", "close", number, "--comment", comment)
        return
    body = issue_body(findings, repo, triage)
    if not dry_run and issue.get("body") != body:
        _gh("issue", "edit", number, "--body", body)


def open_issue(label: str, findings: list[EntryFinding], triage: Triage, repo: str) -> None:
    """Issue NOVA, nunca `reopen`: o `S3` conta pelo createdAt e reprovaria na hora."""
    _gh("label", "create", label, "--force", "--color", "D93F0B",
        "--description", "Entrada do Dependabot vermelha, sem run ou com PR parado")  # fmt: skip
    _gh("issue", "create", "--title", ISSUE_TITLE, "--label", label,
        "--body", issue_body(findings, repo, triage))  # fmt: skip


def sync_issue(
    findings: list[EntryFinding],
    issues: list[dict],
    now: datetime,
    *,
    label: str,
    repo: str,
    dry_run: bool,
) -> None:
    triage = Triage(last_closed_at(issues), now)
    current = next((i for i in issues if i["state"] == "OPEN"), None)
    if current is not None:
        refresh_open(current, findings, triage, repo, dry_run)
        return
    fresh = [f for f in findings if triage.is_fresh(f)]
    if findings and not fresh:
        print(
            f"dependabot-health: {len(findings)} achado(s) triado(s) em {triage.closed_at:%Y-%m-%d}"
        )
    if fresh:
        print(f"dependabot-health: {len(fresh)} achado(s) novo(s) — abre issue `{label}`")
        if not dry_run:
            open_issue(label, findings, triage, repo)


def report(
    entries: list[DependabotEntry],
    runs: list[UpdateRun],
    prs: list[DependabotPr],
    findings: list[EntryFinding],
) -> None:
    opened = sum(pr.closed_at is None for pr in prs)
    print(f"dependabot-health: {len(runs)} runs de entrada agendada lidas")
    print(f"dependabot-health: {len(prs)} PRs do Dependabot lidos ({opened} abertos)")
    for f in findings:
        print(f"dependabot-health: {f.entry} → {f.signal}: {f.evidence}")
    sick = {f.entry for f in findings} & {e.name for e in entries}
    print(f"dependabot-health: {len(entries) - len(sick)}/{len(entries)} entradas saudáveis")


def check_dependabot_health(label: str, dry_run: bool) -> None:
    now = datetime.now(timezone.utc)
    try:
        repo = os.environ["GH_REPO"]
        entries = load_entries()
        runs = scheduled_runs(fetch_runs(repo, now))
        raw_prs = fetch_dependabot_prs(_gh, now - timedelta(days=LOOKBACK_DAYS))
        prs = parse_prs(entries, raw_prs)
        findings = measure_findings(entries, runs, now) + stuck_findings(entries, prs, now)
        report(entries, runs, prs, findings)
        issues = labelled_issues(label)
        sync_issue(findings, issues, now, label=label, repo=repo, dry_run=dry_run)
    # Contrato: nunca run vermelho — ele dispararia o canal de falha do workflow host.
    except Exception as exc:
        print(f"::warning title=dependabot-health sem medição::{type(exc).__name__}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="label da issue (declarado no manifesto)")
    parser.add_argument("--dry-run", action="store_true", help="só reporta, não age")
    args = parser.parse_args()
    check_dependabot_health(args.label, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
