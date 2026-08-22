#!/usr/bin/env python3
"""Vigia a liveness dos workflows agendados declarados em .github/scheduled-workflows.yml (ADR-210 §camada 4): S0 manifesto dessincronizado do disco, S1 workflow desabilitado ou ausente do Actions, S2 sem run agendado dentro da janela, S3 Issue de alerta apodrecendo, GH instrumento mudo; waiver datado degrada para warning até vencer e vira hard-fail depois. FORA do CI, ``gh`` indisponível degrada para pass com warning; DENTRO do CI vira GH e bloqueia — degradar em silêncio no gate recriaria o fail-open. Leitura sem retry por medição, batch por família e orçamento de wall-clock: ver ``Reader``."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / ".github" / "scheduled-workflows.yml"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
_SCHEDULE_RE = re.compile(r"^\s+-\s+cron:", re.MULTILINE)
_HTTP_STATUS_RE = re.compile(r"HTTP (\d{3})")
OVERRIDE_LABELS = ("hotfix", "ops-override")

# p50 medido por chamada = 0,68s (n=11, batch, 2026-08-21; max 0,83s). Acima de
# 10s a leitura já é patológica e o que interessa é devolver GH legível em vez de
# segurar o job — ~15× o p50 é folga suficiente.
CALL_TIMEOUT_S = 10.0
# Teto agregado do run. Sem ele, N chamadas × timeout excedem o
# `timeout-minutes: 4` do job `lint-all` e o desfecho vira job *cancelled* — que
# não nomeia causa nem desbloqueio, pior que a linha GH (ADR-210).
RUN_BUDGET_S = 45.0
PAGE_SIZE = 100


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


@dataclass(frozen=True)
class GhFailure:
    """Leitura que não produziu veredito, com a causa preservada. A versão
    anterior devolvia `None` e apagava `returncode`/`stderr` — apagando
    exatamente o que distingue blip de permissão, e o que teria dispensado a
    varredura de 1000 runs do §Adendo 2026-08-21b."""

    rc: int
    stderr: str

    @property
    def status(self) -> int | None:
        found = _HTTP_STATUS_RE.search(self.stderr)
        return int(found.group(1)) if found else None

    def describe(self) -> str:
        head = f"HTTP {self.status}" if self.status else f"rc={self.rc}"
        first_line = self.stderr.strip().splitlines()[0] if self.stderr.strip() else ""
        return f"{head}: {first_line[:140]}" if first_line else head


_UNREAD = GhFailure(-1, "leitura batch não foi feita")


def today() -> date:
    """Data corrente; `MATHOMS_WATCHDOG_TODAY` permite congelar em teste."""
    override = os.environ.get("MATHOMS_WATCHDOG_TODAY")
    return date.fromisoformat(override) if override else date.today()


def _run(cmd: list[str], timeout: float) -> str | GhFailure:
    """Uma tentativa, sem retry — decidido por medição, não por omissão: em
    2026-08-17 o retry de 5s do trem recuperou 0 de 10 (5×503 devolveram 503 na
    segunda tentativa, 5×403 de permissão são determinísticos). ADR-210."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return GhFailure(-1, f"timeout de {timeout:.0f}s")
    except OSError as exc:
        return GhFailure(-1, str(exc))
    if proc.returncode == 0:
        return proc.stdout
    return GhFailure(proc.returncode, proc.stderr)


@dataclass
class Reader:
    """Leitura do repositório para um run do gate. Faz 1 chamada por FAMÍLIA
    (states de todos os workflows, Issues abertas) em vez de 1 por entrada:
    cada chamada é uma exposição a 5xx, e a superfície era o multiplicador.
    Guarda orçamento de wall-clock e o ledger de falhas."""

    repo: str
    budget_s: float = RUN_BUDGET_S
    calls: int = 0
    failures: list[GhFailure] = field(default_factory=list)
    # Fail-closed por construção: reader sem `for_repo` não tem leitura batch,
    # e "não li" precisa cair em GH, nunca num S1 fabricado ou num pass.
    states: dict[str, str] | GhFailure = field(default_factory=lambda: _UNREAD)
    issues: list[dict] | GhFailure = field(default_factory=lambda: _UNREAD)
    _deadline: float = 0.0

    def __post_init__(self) -> None:
        self._deadline = time.monotonic() + self.budget_s

    @classmethod
    def for_repo(cls, repo: str) -> Reader:
        """Abre o reader já com as duas leituras batch feitas."""
        reader = cls(repo)
        reader.states = read_workflow_states(reader)
        reader.issues = read_open_issues(reader)
        return reader

    def json(self, args: list[str]):
        """Payload decodificado ou `GhFailure` — inclusive por orçamento estourado."""
        left = self._deadline - time.monotonic()
        if left <= 0:
            return self._record(GhFailure(-1, f"orçamento de {self.budget_s:.0f}s esgotado"))
        self.calls += 1
        out = _run(["gh", *args], min(CALL_TIMEOUT_S, left))
        if isinstance(out, GhFailure):
            return self._record(out)
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return self._record(GhFailure(0, "resposta do `gh` não é JSON"))

    def _record(self, failure: GhFailure) -> GhFailure:
        self.failures.append(failure)
        return failure

    def tally(self) -> str:
        return f"{len(self.failures)} de {self.calls} leituras `gh` falharam"


def read_workflow_states(reader: Reader) -> dict[str, str] | GhFailure:
    """`file` → `state` de TODOS os workflows numa chamada. `total_count` maior
    que a página é truncagem: veredito parcial não é veredito."""
    data = reader.json(["api", f"repos/{reader.repo}/actions/workflows?per_page={PAGE_SIZE}"])
    if isinstance(data, GhFailure):
        return data
    listed = data.get("workflows") or []
    total = data.get("total_count", len(listed))
    if total > len(listed):
        return GhFailure(0, f"lista de workflows truncada em {len(listed)} de {total}")
    return {Path(w["path"]).name: w["state"] for w in listed}


def read_open_issues(reader: Reader) -> list[dict] | GhFailure:
    """Issues abertas numa chamada, filtradas por label localmente. `gh issue
    list` ordena newest-first e o S3 caça a MAIS VELHA: página cheia é
    indistinguível de truncagem, e truncar descartaria exatamente as que o
    sinal existe para pegar — fail-open silencioso por inversão de polaridade."""
    args = ["issue", "list", "--repo", reader.repo, "--state", "open"]
    data = reader.json(
        [*args, "--limit", str(PAGE_SIZE), "--json", "number,title,createdAt,labels"]
    )
    if isinstance(data, GhFailure):
        return data
    if len(data) >= PAGE_SIZE:
        return GhFailure(0, f"página cheia ({len(data)}) — truncagem esconderia as mais velhas")
    return data


def _gh_json(args: list[str]):
    """Leitura avulsa, fora do orçamento — só o `repo_slug`, que precede o reader."""
    out = _run(["gh", *args], CALL_TIMEOUT_S)
    if isinstance(out, GhFailure):
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


def last_scheduled_run_age(reader: Reader, filename: str, ref: date) -> float | GhFailure:
    """Idade em dias do run agendado mais recente."""
    # página + `max`, não `runs[0]`: o índice serve cabeça obsoleta de forma
    # intermitente e `per_page=1` não tem como perceber (ADR-210 §Adendo 2026-08-21)
    path = f"repos/{reader.repo}/actions/workflows/{filename}/runs?event=schedule&per_page=10"
    data = reader.json(["api", path])
    if isinstance(data, GhFailure):
        return data
    runs = data.get("workflow_runs") or []
    if not runs:
        return float("inf")
    started = max(
        datetime.fromisoformat(run["run_started_at"].replace("Z", "+00:00")) for run in runs
    )
    return (datetime.combine(ref, datetime.min.time(), timezone.utc) - started).days


def _issue_labels(issue: dict) -> set[str]:
    return {lbl.get("name", "") for lbl in issue.get("labels") or []}


def stale_alert_issues(issues: list[dict], label: str, max_days: int, ref: date) -> list[dict]:
    """Issues daquele label abertas além do limite, já com a idade calculada."""
    stale = []
    for issue in issues:
        if label not in _issue_labels(issue):
            continue
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


def _unreachable(entry: dict, what: str, failure: GhFailure) -> list[Violation]:
    """No CI, `gh` mudo é falha — degradar em silêncio recriaria o fail-open.
    A causa vai na mensagem: 5xx/timeout é transitório e re-rodar resolve;
    4xx é determinístico e re-rodar não resolve."""
    if not running_in_ci():
        return []
    detail = (
        f"`gh` não respondeu para {what} ({failure.describe()}) — instrumento mudo, "
        "não veredito sobre o workflow. Desbloqueio: `gh run rerun --failed`"
    )
    return [Violation("GH", entry["file"], detail)]


def _check_state(reader: Reader, entry: dict) -> list[Violation]:
    if isinstance(reader.states, GhFailure):
        return _unreachable(entry, "state dos workflows", reader.states)
    state = reader.states.get(entry["file"])
    if state is None:
        detail = "declarado no manifesto mas o Actions não conhece o arquivo"
        return [Violation("S1", entry["file"], detail)]
    if state == "active":
        return []
    return [Violation("S1", entry["file"], f"workflow está `{state}` (esperado `active`)")]


def _check_liveness(reader: Reader, entry: dict, ref: date) -> list[Violation]:
    age = last_scheduled_run_age(reader, entry["file"], ref)
    if isinstance(age, GhFailure):
        return _unreachable(entry, "runs agendados", age)
    limit = entry["max_age_days"]
    if age <= limit:
        return []
    seen = "nunca rodou por schedule" if age == float("inf") else f"último run há {age}d"
    return [Violation("S2", entry["file"], f"{seen} (limite {limit}d)")]


def _rot_violation(entry: dict, label: str, max_days: int, issue: dict) -> Violation:
    return Violation(
        "S3",
        entry["file"],
        f"Issue #{issue['number']} (`{label}`) aberta há {issue['age']}d, "
        f"limite {max_days}d: {issue['title']}",
    )


def _check_issue_rot(reader: Reader, entry: dict, ref: date) -> list[Violation]:
    alerts = [a for a in entry.get("alerts") or [] if a.get("max_issue_age_days") is not None]
    if not alerts:
        return []
    if isinstance(reader.issues, GhFailure):
        return _unreachable(entry, "Issues de alerta", reader.issues)
    out = []
    for alert in alerts:
        max_days = alert["max_issue_age_days"]
        stale = stale_alert_issues(reader.issues, alert["label"], max_days, ref)
        out.extend(_rot_violation(entry, alert["label"], max_days, i) for i in stale)
    return out


def check_entry(reader: Reader, entry: dict, ref: date) -> list[Violation]:
    waived, expired = _waiver_state(entry, ref)
    found = _check_state(reader, entry) + _check_liveness(reader, entry, ref)
    found += _check_issue_rot(reader, entry, ref)
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


def _report(violations: list[Violation]) -> int:
    """Modo cron. Exceção já aceita (WAIVED) e instrumento mudo (GH) ficam fora
    do corpo: ele é o gatilho de abertura E o de auto-close, então WAIVED
    mantinha a Issue viva para sempre — medido na #1122, aberta 21 dias só com
    o waiver do nightly. E ruído de API não pode iniciar o relógio do S3."""
    alerting = [v for v in violations if not v.waived and v.signal != "GH"]
    print(render_markdown(alerting) if alerting else "")
    return 0


def collect(reader: Reader, ref: date) -> list[Violation]:
    entries = load_manifest()
    found = check_manifest_coverage(entries)
    for entry in entries:
        found.extend(check_entry(reader, entry, ref))
    return found


def _gate(violations: list[Violation], reader: Reader | None = None) -> int:
    for v in violations:
        print(v.format(), file=sys.stdout if v.waived else sys.stderr)
    blocking = [v for v in violations if not v.waived]
    if not blocking:
        print(f"check_scheduled_workflows: OK ({len(load_manifest())} workflows agendados)")
        return 0
    if pr_has_override():
        print("check_scheduled_workflows: label de override presente — pass forçado")
        return 0
    tally = f" ({reader.tally()})" if reader else ""
    print(
        f"check_scheduled_workflows: {len(blocking)} violação(ões){tally} — religue/conserte "
        "o workflow ou trie a Issue. Linha `GH` é instrumento mudo e cita a causa: 5xx/timeout "
        "é transitório (`gh run rerun --failed`), 4xx é determinístico e re-rodar não resolve. "
        "Label `hotfix`/`ops-override` é exceção de POLÍTICA e apaga a causa do registro "
        "(precedente #1508) — não é o caminho para instabilidade de API",
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
    reader = Reader.for_repo(repo)
    violations = collect(reader, today())
    if args.report:
        return _report(violations)
    return _gate(violations, reader)


if __name__ == "__main__":
    raise SystemExit(main())
