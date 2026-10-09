#!/usr/bin/env python3
"""Saúde das entradas do Dependabot: mantém UMA issue rotulada quando uma entrada de
`.github/dependabot.yml` fica vermelha (2 últimas runs `failure`) ou sem run além do
intervalo. Falha da medição vira warning, nunca run vermelho.
Uso: python3 dev/ci_dependabot_health.py --label X [--dry-run]

Limite declarado: o aviso "cannot open any more pull requests" só aparece na UI do
Dependabot (`network/updates`) — o job sai `success` e este script não o vê."""

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

CONFIG = REPO_ROOT / ".github/dependabot.yml"
WORKFLOW_PATH = "dynamic/dependabot/dependabot-updates"
LOOKBACK_DAYS = 90
STALE_LIMIT = {
    "daily": timedelta(days=3),
    "weekly": timedelta(days=10),
    "monthly": timedelta(days=40),
}
DEFAULT_LIMIT = STALE_LIMIT["weekly"]
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
ISSUE_TITLE = "Dependabot: entrada vermelha ou sem run"
RUNBOOK = "docs/reference/runbooks/python_dependencies.md"


@dataclass(frozen=True)
class DependabotEntry:
    ecosystem: str
    directory: str | None
    interval: str

    @property
    def name(self) -> str:
        return f"{self.ecosystem} {self.directory or '(directories)'}"

    def title_key(self) -> str | None:
        """`<eco> in <dir>` como o título da run agendada o grafa, ou None se não medido."""
        eco = TITLE_ECOSYSTEM.get(self.ecosystem)
        if eco is None or self.directory is None:
            return None
        return f"{eco} in {self.directory.rstrip('/') or '/.'}"


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
    newest_failure: datetime | None = None
    limit: timedelta = DEFAULT_LIMIT

    def is_new_since(self, closed_at: datetime | None, now: datetime) -> bool:
        """Fechar à mão é triagem: só reabre com fato posterior ao fechamento."""
        if closed_at is None:
            return True
        if self.newest_failure is not None:
            return self.newest_failure > closed_at
        return now - closed_at > self.limit


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_entries(path: Path = CONFIG) -> list[DependabotEntry]:
    import yaml

    updates = yaml.safe_load(path.read_text(encoding="utf-8"))["updates"]
    return [
        DependabotEntry(u["package-ecosystem"], u.get("directory"), u["schedule"]["interval"])
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
    return EntryFinding(entry.name, "vermelho", evidence, newest_failure=last_two[0].created_at)


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


def issue_body(findings: list[EntryFinding], repo: str) -> str:
    """Sem data de medição: corpo determinístico não é reeditado a cada run."""
    rows = "\n".join(f"| `{f.entry}` | {f.signal} | {f.evidence} |" for f in findings)
    return (
        f"Entradas de `.github/dependabot.yml` com problema:\n\n"
        f"| Entrada | Sinal | Evidência |\n|---|---|---|\n{rows}\n\n"
        f"## Como triar\n\n"
        f"- **vermelho:** `gh run view <id> --log` na run citada; conserte em PR.\n"
        f"- **sem run / sem correspondência:** em https://github.com/{repo}/network/updates, "
        f"*Check for updates* na entrada. Entrada que nunca completou job deixa de ser agendada.\n"
        f"- **Feche esta issue à mão**, com comentário apontando o PR do conserto. Não espere "
        f"a próxima run passar: o `S3` (10 dias) reprova o `Lint` do próprio PR do conserto.\n"
        f"- O cron só abre issue nova com fato posterior ao fechamento: run `failure` criada "
        f'depois dele, ou o limite de "sem run" vencido de novo.\n\n'
        f'Limite: "cannot open any more pull requests" só aparece na UI do Dependabot.\n\n'
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


def refresh_open(issue: dict, findings: list[EntryFinding], repo: str, dry_run: bool) -> None:
    number = str(issue["number"])
    if not findings:
        if not dry_run:
            _gh("issue", "close", number, "--comment", "Todas as entradas saudáveis.")
        return
    body = issue_body(findings, repo)
    if not dry_run and issue.get("body") != body:
        _gh("issue", "edit", number, "--body", body)


def open_issue(label: str, findings: list[EntryFinding], repo: str) -> None:
    """Issue NOVA, nunca `reopen`: o `S3` conta pelo createdAt e reprovaria na hora."""
    _gh("label", "create", label, "--force", "--color", "D93F0B",
        "--description", "Entrada do Dependabot vermelha ou sem run")  # fmt: skip
    _gh("issue", "create", "--title", ISSUE_TITLE, "--label", label,
        "--body", issue_body(findings, repo))  # fmt: skip


def sync_issue(
    findings: list[EntryFinding],
    issues: list[dict],
    now: datetime,
    *,
    label: str,
    repo: str,
    dry_run: bool,
) -> None:
    current = next((i for i in issues if i["state"] == "OPEN"), None)
    if current is not None:
        refresh_open(current, findings, repo, dry_run)
        return
    closed_at = last_closed_at(issues)
    fresh = [f for f in findings if f.is_new_since(closed_at, now)]
    if findings and not fresh:
        print(f"dependabot-health: {len(findings)} achado(s) triado(s) em {closed_at:%Y-%m-%d}")
    if fresh:
        print(f"dependabot-health: {len(fresh)} achado(s) novo(s) — abre issue `{label}`")
        if not dry_run:
            open_issue(label, findings, repo)


def report(
    entries: list[DependabotEntry], runs: list[UpdateRun], findings: list[EntryFinding]
) -> None:
    print(f"dependabot-health: {len(runs)} runs de entrada agendada lidas")
    for f in findings:
        print(f"dependabot-health: {f.entry} → {f.signal}: {f.evidence}")
    sick = {f.entry for f in findings}
    print(f"dependabot-health: {len(entries) - len(sick)}/{len(entries)} entradas saudáveis")


def check_dependabot_health(label: str, dry_run: bool) -> None:
    now = datetime.now(timezone.utc)
    try:
        repo = os.environ["GH_REPO"]
        entries = load_entries()
        runs = scheduled_runs(fetch_runs(repo, now))
        findings = measure_findings(entries, runs, now)
        report(entries, runs, findings)
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
