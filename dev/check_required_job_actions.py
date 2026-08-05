#!/usr/bin/env python3
"""Veda `runs.using: docker` e action não-registrada em job do fecho `required_jobs` (ADR-320 §Emenda 2026-08-05): checagem 100% offline contra `.github/third-party-actions.yml` — rede só na adoção manual de action nova, nunca no gate."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / ".github" / "third-party-actions.yml"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
SAFE_RUNS_USING = {"node16", "node20", "node24", "composite"}


@dataclass(frozen=True)
class Violation:
    """Achado do gate; `action_ref` é `owner/repo` sem o `@ref`."""

    workflow: str
    job: str
    action_ref: str
    reason: str

    def format(self) -> str:
        return f"{self.workflow}::{self.job} usa `{self.action_ref}` — {self.reason}"


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _action_ref(uses: str) -> str:
    """`owner/repo@ref` ou `owner/repo/subpath@ref` → `owner/repo` (sem `@ref`)."""
    return uses.split("@", 1)[0]


def _job_uses_refs(workflow_path: Path, job_name: str) -> list[str]:
    doc = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    job = (doc.get("jobs") or {}).get(job_name) or {}
    steps = job.get("steps") or []
    return [_action_ref(step["uses"]) for step in steps if step.get("uses")]


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    registry = load_registry()
    violations = check_all(registry)
    if not violations:
        print("✓ nenhuma action Docker / não-registrada em job required.")
        return 0

    print(f"✗ {len(violations)} violação(ões) — job required com action de risco:\n")
    for v in violations:
        print(f"  {v.format()}")
    print(
        "\nRegistre a action em .github/third-party-actions.yml (após confirmar "
        "runs.using offline-por-adoção), ou mova o job para fora do fecho "
        "required_jobs, ou troque por script inline — ver comentário do arquivo."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
