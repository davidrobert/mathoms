#!/usr/bin/env python3
"""Vigia a liveness dos workflows agendados declarados em .github/scheduled-workflows.yml (ADR-210 §camada 4): S1 workflow desabilitado, S2 sem run agendado dentro da janela, S3 Issue de alerta apodrecendo; waiver datado degrada para warning até vencer e vira hard-fail depois; offline/sem ``gh`` degrada para pass com warning."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / ".github" / "scheduled-workflows.yml"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
_SCHEDULE_RE = re.compile(r"^\s+-\s+cron:", re.MULTILINE)
OVERRIDE_LABELS = ("hotfix", "ops-override")


@dataclass(frozen=True)
class Violation:
    """Achado do watchdog; `waived` marca entrada sob waiver ainda válido."""

    signal: str
    workflow: str
    detail: str
    waived: bool = False

    def format(self) -> str:
        mark = "WAIVED" if self.waived else self.signal
        return f"[{mark}] {self.workflow}: {self.detail}"


def today() -> date:
    """Data corrente; `MATHOMS_WATCHDOG_TODAY` permite congelar em teste."""
    override = os.environ.get("MATHOMS_WATCHDOG_TODAY")
    return date.fromisoformat(override) if override else date.today()


def _run(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _gh_json(args: list[str]):
    out = _run(["gh", *args])
    if out is None:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def repo_slug() -> str | None:
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    data = _gh_json(["repo", "view", "--json", "nameWithOwner"])
    return data.get("nameWithOwner") if data else None


def load_manifest() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return data.get("workflows", [])


def scheduled_files_on_disk() -> set[str]:
    """Workflows com bloco `schedule:` — a fonte contra a qual o manifesto é conferido."""
    found = set()
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        if _SCHEDULE_RE.search(path.read_text(encoding="utf-8")):
            found.add(path.name)
    return found


def check_manifest_coverage(entries: list[dict]) -> list[Violation]:
    declared = {e["file"] for e in entries}
    orphans = scheduled_files_on_disk() - declared
    ghosts = declared - scheduled_files_on_disk()
    out = [
        Violation("S0", f, "tem `schedule:` mas não está no manifesto — adicione entrada")
        for f in sorted(orphans)
    ]
    out += [
        Violation("S0", f, "está no manifesto mas não tem `schedule:` — remova a entrada")
        for f in sorted(ghosts)
    ]
    return out


def workflow_state(repo: str, filename: str) -> str | None:
    data = _gh_json(["api", f"repos/{repo}/actions/workflows/{filename}"])
    return data.get("state") if data else None


def last_scheduled_run_age(repo: str, filename: str, ref: date) -> float | None:
    """Idade em dias do run agendado mais recente; None se a API não respondeu."""
    path = f"repos/{repo}/actions/workflows/{filename}/runs?event=schedule&per_page=1"
    data = _gh_json(["api", path])
    if data is None:
        return None
    runs = data.get("workflow_runs") or []
    if not runs:
        return float("inf")
    started = datetime.fromisoformat(runs[0]["run_started_at"].replace("Z", "+00:00"))
    return (datetime.combine(ref, datetime.min.time(), timezone.utc) - started).days


def stale_alert_issues(label: str, max_days: int, ref: date) -> list[dict] | None:
    data = _gh_json(
        ["issue", "list", "--label", label, "--state", "open", "--json", "number,title,createdAt"]
    )
    if data is None:
        return None
    stale = []
    for issue in data:
        created = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00")).date()
        age = (ref - created).days
        if age > max_days:
            stale.append({**issue, "age": age})
    return stale


def _waiver_state(entry: dict, ref: date) -> tuple[bool, Violation | None]:
    """(waiver ativo?, violação se vencido). Waiver vencido é hard-fail próprio."""
    waiver = entry.get("waiver")
    if not waiver:
        return False, None
    until = date.fromisoformat(str(waiver["until"]))
    if until >= ref:
        return True, None
    detail = f"waiver venceu em {until} — resolva a causa ou renove com justificativa"
    return False, Violation("WAIVER", entry["file"], detail)


def running_in_ci() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _unreachable(entry: dict, what: str) -> list[Violation]:
    """No CI, `gh` mudo é falha — degradar em silêncio recriaria o fail-open."""
    if not running_in_ci():
        return []
    detail = f"`gh` não respondeu para {what} — cheque permissions do job (actions/issues: read)"
    return [Violation("GH", entry["file"], detail)]


def _check_state(repo: str, entry: dict) -> list[Violation]:
    state = workflow_state(repo, entry["file"])
    if state is None:
        return _unreachable(entry, "state do workflow")
    if state == "active":
        return []
    return [Violation("S1", entry["file"], f"workflow está `{state}` (esperado `active`)")]


def _check_liveness(repo: str, entry: dict, ref: date) -> list[Violation]:
    age = last_scheduled_run_age(repo, entry["file"], ref)
    if age is None:
        return _unreachable(entry, "runs agendados")
    limit = entry["max_age_days"]
    if age <= limit:
        return []
    seen = "nunca rodou por schedule" if age == float("inf") else f"último run há {age}d"
    return [Violation("S2", entry["file"], f"{seen} (limite {limit}d)")]


def _check_issue_rot(entry: dict, ref: date) -> list[Violation]:
    out = []
    for alert in entry.get("alerts") or []:
        max_days = alert.get("max_issue_age_days")
        if max_days is None:
            continue
        stale = stale_alert_issues(alert["label"], max_days, ref)
        if stale is None:
            out.extend(_unreachable(entry, f"Issues `{alert['label']}`"))
            continue
        for issue in stale:
            out.append(
                Violation(
                    "S3",
                    entry["file"],
                    f"Issue #{issue['number']} (`{alert['label']}`) aberta há "
                    f"{issue['age']}d, limite {max_days}d: {issue['title']}",
                )
            )
    return out


def check_entry(repo: str, entry: dict, ref: date) -> list[Violation]:
    waived, expired = _waiver_state(entry, ref)
    found = _check_state(repo, entry) + _check_liveness(repo, entry, ref)
    found += _check_issue_rot(entry, ref)
    if waived:
        found = [Violation(v.signal, v.workflow, v.detail, waived=True) for v in found]
    return found + ([expired] if expired else [])


def pr_has_override() -> bool:
    """Label de escape no PR — sem isso, o PR que conserta o drift não mergeia."""
    labels = os.environ.get("MATHOMS_PR_LABELS", "")
    return any(lbl in labels.split(",") for lbl in OVERRIDE_LABELS)


def render_markdown(violations: list[Violation]) -> str:
    lines = ["| sinal | workflow | detalhe |", "|---|---|---|"]
    for v in violations:
        mark = "WAIVED" if v.waived else v.signal
        lines.append(f"| `{mark}` | `{v.workflow}` | {v.detail} |")
    return "\n".join(lines)


def collect(repo: str, ref: date) -> list[Violation]:
    entries = load_manifest()
    found = check_manifest_coverage(entries)
    for entry in entries:
        found.extend(check_entry(repo, entry, ref))
    return found


def _gate(violations: list[Violation]) -> int:
    for v in violations:
        print(v.format(), file=sys.stdout if v.waived else sys.stderr)
    blocking = [v for v in violations if not v.waived]
    if not blocking:
        print(f"check_scheduled_workflows: OK ({len(load_manifest())} workflows agendados)")
        return 0
    if pr_has_override():
        print("check_scheduled_workflows: label de override presente — pass forçado")
        return 0
    print(
        f"check_scheduled_workflows: {len(blocking)} violação(ões) — religue/conserte o "
        "workflow, trie a Issue, ou aplique label `hotfix`/`ops-override`",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        action="store_true",
        help="modo cron: imprime markdown e sempre sai 0 (o workflow abre a Issue)",
    )
    args = parser.parse_args()
    repo = repo_slug()
    if repo is None:
        if running_in_ci():
            print("check_scheduled_workflows: sem repo slug DENTRO do CI", file=sys.stderr)
            return 1
        print("check_scheduled_workflows: gh indisponível — pass gracioso (offline)")
        return 0
    violations = collect(repo, today())
    if args.report:
        print(render_markdown(violations) if violations else "")
        return 0
    return _gate(violations)


if __name__ == "__main__":
    raise SystemExit(main())
