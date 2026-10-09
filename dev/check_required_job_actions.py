#!/usr/bin/env python3
"""Registro de actions amarrado ao `@ref` (ADR-320 §Emendas 2026-08-03 e 2026-10-08): docker vedado em job required, runtime abaixo de node24 vedado em todo workflow — 100% offline; rede só em `--suggest`."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / ".github" / "third-party-actions.yml"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
SAFE_RUNS_USING = {"node24", "composite"}
# Fora de job required, docker segue aceito (ADR-320 §Emenda 2026-08-03); o piso é de runtime.
RUNTIME_OK = SAFE_RUNS_USING | {"docker"}


@dataclass(frozen=True)
class Violation:
    """Achado do gate; `action_ref` é `owner/repo` sem o `@ref`."""

    workflow: str
    job: str
    action_ref: str
    reason: str

    def format(self) -> str:
        return f"{self.workflow}::{self.job} usa `{self.action_ref}` — {self.reason}"


@dataclass(frozen=True)
class ActionUse:
    """Um `uses:` externo de step: `owner/repo[/subpath]` + o ref exato (tag ou SHA)."""

    workflow: str
    job: str
    action: str
    ref: str


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _action_ref(uses: str) -> str:
    """`owner/repo@ref` ou `owner/repo/subpath@ref` → `owner/repo` (sem `@ref`)."""
    return uses.split("@", 1)[0]


def _jobs(workflow_path: Path) -> dict:
    return yaml.safe_load(workflow_path.read_text(encoding="utf-8")).get("jobs") or {}


def _job_uses_refs(workflow_path: Path, job_name: str) -> list[str]:
    steps = (_jobs(workflow_path).get(job_name) or {}).get("steps") or []
    return [_action_ref(step["uses"]) for step in steps if step.get("uses")]


def _external_uses(job: dict | None) -> list[str]:
    """Local (`./.github/actions/x`) é ignorado: não há versão externa a registrar."""
    steps = (job or {}).get("steps") or []
    return [s["uses"] for s in steps if s.get("uses") and not s["uses"].startswith(".")]


def iter_action_uses(workflow_dir: Path) -> list[ActionUse]:
    return [
        ActionUse(path.name, job_name, uses.partition("@")[0], uses.partition("@")[2])
        for path in sorted(workflow_dir.glob("*.y*ml"))
        for job_name, job in _jobs(path).items()
        for uses in _external_uses(job)
    ]


def _check_action(
    registry: dict, workflow_file: str, job_name: str, action_ref: str
) -> Violation | None:
    entry = registry["actions"].get(action_ref)
    if entry is None:
        return Violation(
            workflow_file,
            job_name,
            action_ref,
            "não registrada em .github/third-party-actions.yml",
        )
    runs_using = entry.get("runs_using", "")
    if runs_using not in SAFE_RUNS_USING:
        return Violation(
            workflow_file,
            job_name,
            action_ref,
            f"runs.using={runs_using!r} vedado em job required (ADR-320)",
        )
    return None


def check_job(registry: dict, workflow_file: str, job_name: str) -> list[Violation]:
    """Local (self-hosted) `uses:` sem `@` — ex.: `./.github/actions/x` — é ignorado: não há registry externo a violar."""
    workflow_path = WORKFLOW_DIR / workflow_file
    checked = (
        _check_action(registry, workflow_file, job_name, ref)
        for ref in _job_uses_refs(workflow_path, job_name)
        if not ref.startswith(".")
    )
    return [v for v in checked if v is not None]


def check_all(registry: dict) -> list[Violation]:
    violations: list[Violation] = []
    for workflow_file, job_names in registry["required_jobs"].items():
        for job_name in job_names:
            violations.extend(check_job(registry, workflow_file, job_name))
    return violations


def _pinned_use_problem(entry: dict | None, use: ActionUse) -> str | None:
    if entry is None:
        return "não registrada em .github/third-party-actions.yml"
    if str(entry.get("ref", "")) != use.ref:
        return f"@{use.ref} ≠ ref registrado {entry.get('ref')!r} — runs_using do registro não descreve esta versão"
    if entry.get("runs_using") not in RUNTIME_OK:
        return f"runs.using={entry.get('runs_using')!r} abaixo do piso node24 (ADR-320 §Emenda 2026-10-08)"
    return None


def _check_pinned_use(registry: dict, use: ActionUse) -> Violation | None:
    reason = _pinned_use_problem(registry["actions"].get(use.action), use)
    return Violation(use.workflow, use.job, use.action, reason) if reason else None


def check_pinned_refs(registry: dict) -> list[Violation]:
    """Todo workflow, não só o fecho required: hard-fail de runtime derruba nightly/security calado."""
    checked = (_check_pinned_use(registry, use) for use in iter_action_uses(WORKFLOW_DIR))
    return [v for v in checked if v is not None]


def _gh_file(repo: str, path: str, ref: str) -> str | None:
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        return None
    return base64.b64decode(json.loads(proc.stdout)["content"]).decode()


def _fetch_runs_using(action: str, ref: str) -> str:
    parts = action.split("/")
    repo, prefix = "/".join(parts[:2]), "".join(f"{p}/" for p in parts[2:])
    found = (_gh_file(repo, f"{prefix}{name}", ref) for name in ("action.yml", "action.yaml"))
    content = next((c for c in found if c is not None), None)
    if content is None:
        return "?"
    return str((yaml.safe_load(content).get("runs") or {}).get("using", "?"))


def suggest_entries(violations: list[Violation]) -> list[str]:
    """Rede (gh api) só aqui, nunca no gate: imprime a entrada pronta para o registro."""
    pending = {(u.action, u.ref) for u in iter_action_uses(WORKFLOW_DIR)}
    stale = {v.action_ref for v in violations}
    return [
        f'  {action}:\n    ref: "{ref}"\n    runs_using: {_fetch_runs_using(action, ref)}\n'
        f'    verified_at: "{date.today().isoformat()}"'
        for action, ref in sorted(pending)
        if action in stale
    ]


REMEDIATION_HINT = (
    "\nRode `python3 dev/check_required_job_actions.py --suggest` (usa rede) e copie a "
    "entrada para .github/third-party-actions.yml; se runs.using vier docker, mova o "
    "job para fora de required_jobs ou troque por script inline — ver cabeçalho do registro."
)


def _remediation(violations: list[Violation]) -> str:
    entries = "\n".join(suggest_entries(violations))
    return f"\nEntradas para .github/third-party-actions.yml (confira runs.using):\n\n{entries}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suggest", action="store_true", help="usa rede: imprime entradas novas do registro"
    )
    args = parser.parse_args()

    registry = load_registry()
    violations = check_all(registry) + check_pinned_refs(registry)
    if not violations:
        print(
            "✓ toda action registrada no ref em uso; nada docker em required, nada abaixo de node24."
        )
        return 0

    print(f"✗ {len(violations)} violação(ões) de action:\n")
    for v in violations:
        print(f"  {v.format()}")
    print(_remediation(violations) if args.suggest else REMEDIATION_HINT)
    return 1


if __name__ == "__main__":
    sys.exit(main())
