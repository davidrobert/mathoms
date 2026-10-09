#!/usr/bin/env python3
"""Alerta do Dependabot com conserto publicado, sem PR e além do SLO de remediação
(CRITICAL 72h · HIGH 14d, relógio = detecção): mantém UMA issue rotulada. O Dependabot
não abre PR quando o conserto exige major do pai, e o alerta fica aberto calado.
Falha da medição vira linha "sem medição" (4xx, lista truncada) ou warning (5xx), nunca
run vermelho. Uso: python3 dev/ci_dependabot_alert_slo.py --label X [--dry-run]

Limites declarados: `first_patched_version` é o de hoje, não o do dia do vencimento; o
grafo de dependências lê os `.in`/`pyproject.toml` do pip, não o `requirements.lock`, então
transitiva pip fica só com o `pip-audit` (`docs/reference/runbooks/security_gates.md`)."""

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

from dev.ci_advance_automerge_train import GhCallFailed, _gh  # noqa: E402
from dev.ci_dependabot_health import load_entries, parse_ts  # noqa: E402
from dev.ci_dependabot_stuck_prs import split_branch  # noqa: E402

SLO = {"critical": timedelta(hours=72), "high": timedelta(days=14)}
# Co-design sre-devops 2026-10-09: o Dependabot tenta o PR em horas depois que o advisory
# muda. A carência só adia o disparo; reiniciar o relógio deixaria edição cosmética do
# advisory adiar um HIGH para sempre.
ADVISORY_GRACE = timedelta(hours=24)
# `dependency.package.ecosystem` do alerta → segmento da branch `dependabot/<eco>/…`.
# Medido em 2026-10-09 sobre os 194 alertas do repo: só `npm` (184) e `go` (10).
BRANCH_ECOSYSTEM = {
    "npm": "npm_and_yarn",
    "go": "go_modules",
    "pip": "pip",
    "actions": "github_actions",
}
ALERT_FIELDS = (
    ".[] | {number, html_url, created_at, manifest: .dependency.manifest_path,"
    " ecosystem: .dependency.package.ecosystem, package: .dependency.package.name,"
    " severity: .security_advisory.severity, advisory_updated_at: .security_advisory.updated_at,"
    " patched: .security_vulnerability.first_patched_version.identifier}"
)
# `gh pr list --json commits` pede 100 PRs × 100 commits × 100 autores por página e estoura
# o teto de 500k nós do GraphQL (medido em 2026-10-09 com 50 PRs: 505.050). Sem `authors`,
# 100 PRs × 20 commits cabem; `issueCount` acima dos nós lidos denuncia lista cortada.
OPEN_PRS_QUERY = """query($q: String!) {
  search(query: $q, type: ISSUE, first: 100) {
    issueCount
    nodes { ... on PullRequest { number url headRefName
      commits(first: 20) { nodes { commit { message } } } } }
  }
}"""
# Metadata que o próprio Dependabot grava no commit (o mesmo que o fetch-metadata lê);
# pacote com escopo vem entre aspas YAML: `- dependency-name: "@eslint/js"`.
DEPENDENCY_NAME = re.compile(r'^- dependency-name: "?([^"\s]+)"?$', re.MULTILINE)
BOT_LOGIN = "github-actions[bot]"
ISSUE_TITLE = "Segurança: alerta do Dependabot com conserto, sem PR e além do SLO"
ALERT_ROW = re.compile(r"^\| \[#(?P<number>\d+)\]\([^)]*\) \| \w+ \| `(?P<package>[^`]+)`", re.M)
RUNBOOK = "docs/reference/runbooks/security_gates.md"


@dataclass(frozen=True)
class DependabotAlert:
    number: int
    url: str
    severity: str
    ecosystem: str
    directory: str
    package: str
    patched: str | None
    created_at: datetime
    advisory_updated_at: datetime

    def deadline(self) -> datetime | None:
        slo = SLO.get(self.severity)
        return self.created_at + slo if slo else None


@dataclass(frozen=True)
class OpenUpdate:
    """PR aberto do Dependabot: os pacotes saem do metadata, o diretório da branch."""

    number: int
    url: str
    ecosystem: str
    directory: str | None
    packages: frozenset[str]

    def covers(self, alert: DependabotAlert) -> bool:
        key = (self.ecosystem, self.directory)
        return key == (alert.ecosystem, alert.directory) and alert.package in self.packages


@dataclass(frozen=True)
class Verdict:
    alert: DependabotAlert
    reason: str
    breach: bool = False


@dataclass(frozen=True)
class Measurement:
    """`prs` None = lista de PRs sem medição: alerta vencido vira linha, nunca silêncio."""

    alerts: list[DependabotAlert]
    prs: list[OpenUpdate] | None
    blind: list[str]


def manifest_directory(manifest_path: str) -> str:
    """`frontend/package-lock.json` → `/frontend`; manifesto na raiz → `/`."""
    parent = manifest_path.rpartition("/")[0]
    return f"/{parent}" if parent else "/"


def normalize_directory(directory: str) -> str:
    return "/" + directory.strip("/")


def parse_alert(raw: dict) -> DependabotAlert:
    return DependabotAlert(
        number=raw["number"],
        url=raw["html_url"],
        severity=raw["severity"],
        ecosystem=BRANCH_ECOSYSTEM.get(raw["ecosystem"], raw["ecosystem"]),
        directory=manifest_directory(raw["manifest"]),
        package=raw["package"],
        patched=raw.get("patched"),
        created_at=parse_ts(raw["created_at"]),
        advisory_updated_at=parse_ts(raw["advisory_updated_at"]),
    )


def branch_directories(alerts: list[DependabotAlert]) -> dict[str, set[str]]:
    """Diretórios do yml + os dos alertas: security update sem entrada (go) também resolve."""
    dirs: dict[str, set[str]] = {}
    for entry in load_entries():
        eco, directory = entry.branch_key()
        if directory is not None:
            dirs.setdefault(eco, set()).add(normalize_directory(directory))
    for alert in alerts:
        dirs.setdefault(alert.ecosystem, set()).add(alert.directory)
    return dirs


def parse_update(raw: dict, dirs: dict[str, set[str]]) -> OpenUpdate:
    ecosystem = raw["headRefName"].split("/")[1]
    _, directory, _ = split_branch(raw["headRefName"], dirs.get(ecosystem, set()))
    messages = (node["commit"]["message"] for node in raw["commits"]["nodes"])
    packages = frozenset(m for msg in messages for m in DEPENDENCY_NAME.findall(msg))
    return OpenUpdate(raw["number"], raw["url"], ecosystem, directory, packages)


def judge(alert: DependabotAlert, prs: list[OpenUpdate] | None, now: datetime) -> Verdict:
    deadline = alert.deadline()
    if deadline is None:
        return Verdict(alert, f"{alert.severity}: best-effort, fora do SLO")
    if alert.patched is None:
        return Verdict(alert, "sem versão corrigida publicada")
    if now <= deadline:
        return Verdict(alert, f"dentro do SLO até {deadline:%Y-%m-%d %H:%M} UTC")
    if now - alert.advisory_updated_at < ADVISORY_GRACE:
        return Verdict(alert, "advisory mudou há menos de 24h: espera o PR do Dependabot")
    return _judge_coverage(alert, prs, deadline)


def _judge_coverage(
    alert: DependabotAlert, prs: list[OpenUpdate] | None, deadline: datetime
) -> Verdict:
    if prs is None:
        return Verdict(alert, f"venceu em {deadline:%Y-%m-%d}; PRs sem medição", breach=True)
    pr = next((p for p in prs if p.covers(alert)), None)
    if pr is not None:
        return Verdict(alert, f"PR #{pr.number} do Dependabot aberto")
    return Verdict(alert, f"venceu em {deadline:%Y-%m-%d}", breach=True)


def fetch_alerts(repo: str) -> list[DependabotAlert]:
    url = f"repos/{repo}/dependabot/alerts?state=open&per_page=100"
    raw = _gh("api", "--paginate", url, "--jq", ALERT_FIELDS)
    return [parse_alert(json.loads(line)) for line in raw.splitlines() if line.strip()]


def fetch_open_updates(repo: str, dirs: dict[str, set[str]]) -> list[OpenUpdate]:
    query = f"repo:{repo} is:pr is:open author:app/dependabot"
    out = _gh("api", "graphql", "-f", f"query={OPEN_PRS_QUERY}", "-f", f"q={query}")
    search = json.loads(out)["data"]["search"]
    nodes = search["nodes"]
    if search["issueCount"] > len(nodes):
        raise ListTruncated(f"lista de PRs cortada: {len(nodes)} de {search['issueCount']}")
    return [parse_update(node, dirs) for node in nodes]


class ListTruncated(ValueError):
    """Truncar decide silêncio sem medir: vira linha, igual a um 4xx."""


def blind_reason(source: str, exc: Exception) -> str | None:
    """4xx e lista cortada são veredito (linha na issue); 5xx/timeout é warning."""
    if isinstance(exc, ListTruncated):
        return f"{source}: {exc}"
    if isinstance(exc, GhCallFailed) and exc.is_verdict:
        return f"{source}: HTTP {exc.status} — {exc.stderr.strip()[:200]}"
    return None


def measure(repo: str) -> Measurement:
    try:
        alerts = fetch_alerts(repo)
    except (GhCallFailed, ListTruncated) as exc:
        if (reason := blind_reason("alertas do Dependabot", exc)) is None:
            raise
        return Measurement([], [], [reason])
    try:
        return Measurement(alerts, fetch_open_updates(repo, branch_directories(alerts)), [])
    except (GhCallFailed, ListTruncated) as exc:
        if (reason := blind_reason("PRs do Dependabot", exc)) is None:
            raise
        return Measurement(alerts, None, [reason])


def issue_body(breaches: list[Verdict], blind: list[str]) -> str:
    """Sem data de medição: corpo determinístico não é reeditado a cada run."""
    parts = ["Alertas do Dependabot com versão corrigida publicada, sem PR aberto do "
             "Dependabot e além do SLO de remediação (CRITICAL 72h · HIGH 14d, contados "
             "da detecção do alerta)."]  # fmt: skip
    if breaches:
        parts.append(_breach_table(breaches))
    if blind:
        parts.append("## Sem medição\n\n" + "\n".join(f"- {reason}" for reason in blind))
    parts.append(triage_guide())
    return "\n\n".join(parts)


def _breach_table(breaches: list[Verdict]) -> str:
    head = "| Alerta | Severidade | Pacote | Diretório | Corrigido em | Situação |\n|---|---|---|---|---|---|"
    rows = [
        f"| [#{v.alert.number}]({v.alert.url}) | {v.alert.severity} | `{v.alert.package}` "
        f"| `{v.alert.directory}` | `{v.alert.patched}` | {v.reason} |"
        for v in breaches
    ]
    return "\n".join([head, *rows])


def triage_guide() -> str:
    return (
        "## Como triar\n\n"
        "- **Conserte:** bump do pacote em PR; se o conserto exige major do pai (o caso que "
        "o Dependabot não abre), bump do pai ou lane de migração. A linha some quando o "
        "alerta fecha ou quando um PR do Dependabot passa a cobrir o pacote.\n"
        "- **Aceite o risco:** *Dismiss* do alerta no GitHub com motivo e comentário (fica "
        "registrado quem, quando e por quê). É o único silêncio sem conserto.\n"
        "- **Fechar esta issue à mão destrava o `S3` só até o próximo cron (02:00 UTC):** com "
        "violação viva ela é reaberta, a mesma issue, com a idade preservada.\n"
        "- PR do Dependabot aberto silencia o alerta aqui; se ele parar, quem avisa é o "
        '"PR parado" (5 dias) da issue `ops-dependabot-red`.\n\n'
        "Cobertura: o que o dependency graph lê (npm e go; do pip, só `.in` e "
        "`pyproject.toml`, sem o `requirements.lock`). Transitiva pip fica com o `pip-audit`.\n\n"
        f"Runbook: `{RUNBOOK}` §SLO de remediação. Política: ADR-230 §Emenda 2026-10-09.\n\n"
        "_Mantida por `dev/ci_dependabot_alert_slo.py`; `S3` de 7 dias no manifesto._"
    )


def close_comment(previous_body: str) -> str:
    gone = [f"#{m['number']} (`{m['package']}`)" for m in ALERT_ROW.finditer(previous_body)]
    tail = "Nenhum alerta com conserto além do SLO sem PR."
    return f"Zerou: {', '.join(gone)}. {tail}" if gone else tail


def labelled_issues(label: str) -> list[dict]:
    """Pelo `_gh` deste módulo: o do `ci_dependabot_health` escaparia do fake nos testes."""
    fields = "number,state,body,closedAt"
    out = _gh(
        "issue", "list", "--state", "all", "--label", label, "--limit", "20", "--json", fields
    )
    return json.loads(out)


def closed_by_human(repo: str, issue: dict) -> bool:
    """Fechamento humano é soneca, não triagem: a violação viva reabre a MESMA issue."""
    login = _gh("api", f"repos/{repo}/issues/{issue['number']}", "--jq", ".closed_by.login")
    return login.strip() != BOT_LOGIN


def sync_issue(
    breaches: list[Verdict],
    blind: list[str],
    issues: list[dict],
    *,
    label: str,
    repo: str,
    dry_run: bool,
) -> str:
    """Devolve a ação (para o log e os testes); `dry_run` decide mas não executa."""
    action, number, body = _decide(breaches, blind, issues, repo)
    if not dry_run:
        _apply(action, number, body, label)
    return action


def _decide(
    breaches: list[Verdict], blind: list[str], issues: list[dict], repo: str
) -> tuple[str, str, str]:
    current = next((i for i in issues if i["state"] == "OPEN"), None)
    alive = bool(breaches or blind)
    body = issue_body(breaches, blind) if alive else ""
    if current is not None:
        return _decide_open(current, alive, body)
    if not alive:
        return "nada", "", ""
    last = _last_closed(issues)
    if last is not None and closed_by_human(repo, last):
        return "reabre", str(last["number"]), body
    return "cria", "", body


def _decide_open(current: dict, alive: bool, body: str) -> tuple[str, str, str]:
    number = str(current["number"])
    if not alive:
        return "fecha", number, close_comment(current.get("body") or "")
    return ("mantém" if current.get("body") == body else "edita"), number, body


def _last_closed(issues: list[dict]) -> dict | None:
    closed = [i for i in issues if i.get("closedAt")]
    return max(closed, key=lambda i: parse_ts(i["closedAt"])) if closed else None


def _apply(action: str, number: str, text: str, label: str) -> None:
    if action == "fecha":
        _gh("issue", "close", number, "--comment", text)
    elif action == "edita":
        _gh("issue", "edit", number, "--body", text)
    elif action == "reabre":
        _gh("issue", "reopen", number, "--comment", "Violação viva: fechar à mão não é triagem.")
        _gh("issue", "edit", number, "--body", text)
    elif action == "cria":
        _gh("label", "create", label, "--force", "--color", "B60205",
            "--description", "Alerta do Dependabot com conserto, sem PR e além do SLO")  # fmt: skip
        _gh("issue", "create", "--title", ISSUE_TITLE, "--label", label, "--body", text)


def report(measurement: Measurement, verdicts: list[Verdict]) -> None:
    tracked = [v for v in verdicts if v.alert.severity in SLO]
    print(f"dependabot-alert-slo: {len(measurement.alerts)} alertas abertos lidos")
    if measurement.prs is not None:
        print(f"dependabot-alert-slo: {len(measurement.prs)} PRs abertos do Dependabot lidos")
    for v in tracked:
        a = v.alert
        print(
            f"dependabot-alert-slo: #{a.number} {a.severity} `{a.package}` {a.directory} → {v.reason}"
        )
    for reason in measurement.blind:
        print(f"dependabot-alert-slo: sem medição — {reason}")
    breaches = sum(v.breach for v in verdicts)
    print(
        f"dependabot-alert-slo: {breaches} além do SLO sem PR; {len(verdicts) - len(tracked)} MEDIUM/LOW"
    )


def check_alert_slo(label: str, dry_run: bool) -> None:
    now = datetime.now(timezone.utc)
    try:
        repo = os.environ["GH_REPO"]
        measurement = measure(repo)
        verdicts = [judge(alert, measurement.prs, now) for alert in measurement.alerts]
        report(measurement, verdicts)
        breaches = [v for v in verdicts if v.breach]
        issues = labelled_issues(label)
        action = sync_issue(
            breaches, measurement.blind, issues, label=label, repo=repo, dry_run=dry_run
        )
        print(f"dependabot-alert-slo: issue `{label}` → {action}{' (dry-run)' * dry_run}")
    # Contrato: nunca run vermelho — ele dispararia o canal de falha do workflow host.
    except Exception as exc:
        print(f"::warning title=dependabot-alert-slo sem medição::{type(exc).__name__}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="label da issue (declarado no manifesto)")
    parser.add_argument("--dry-run", action="store_true", help="só reporta, não age")
    args = parser.parse_args()
    check_alert_slo(args.label, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
