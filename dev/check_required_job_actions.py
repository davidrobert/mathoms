#!/usr/bin/env python3
"""Runtime de action lido do lock pelo `uses:` exato (ADR-320 §Emendas 2026-08-03 e 2026-10-09 (runtime pelo lock)): em job required só node24 de action admitida; em todo workflow, piso node24/composite/docker — 100% offline contra `.github/actions.lock.yml` e `.github/third-party-actions.yml`."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.check_action_inputs import (  # noqa: E402
    LOCK_PATH,
    REFRESH_CMD,
    Lock,
    StepUse,
    collect_step_uses,
    load_lock,
    unsupported_form,
)

REGISTRY_PATH = REPO_ROOT / ".github" / "third-party-actions.yml"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
EMENDA = "ADR-320 §Emenda 2026-10-09 (runtime pelo lock)"
# Lista de permitidos, não de proibidos: um `node26` reprova até alguém incluí-lo.
RUNTIME_FLOOR = frozenset({"node24", "composite", "docker"})
# Composite pode embrulhar action docker ou `docker run` num step — o #1161 de novo.
REQUIRED_RUNS_USING = frozenset({"node24"})
REGISTRY_KEYS = frozenset({"actions", "required_jobs"})
# Job agregador de cada status check exigido pelo Ruleset `main-protection`.
CLOSURE_ROOTS = {"ci.yml": "all-green", "pr-quality.yml": "title-lint"}


@dataclass(frozen=True)
class Violation:
    """Achado do gate; `action_ref` é o `uses:` exato, vazio quando o achado é do job ou do registro."""

    workflow: str
    job: str
    action_ref: str
    reason: str

    def format(self) -> str:
        where = f"{self.workflow}::{self.job}" if self.job else self.workflow
        if not self.action_ref:
            return f"{where} — {self.reason}"
        return f"{where} usa `{self.action_ref}` — {self.reason}"


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _action_name(uses: str) -> str:
    """A política vale por action (`owner/repo[/subpath]`); o fato de runtime, por versão."""
    return uses.partition("@")[0]


def _violation(site: StepUse, reason: str) -> Violation:
    return Violation(site.workflow, site.job, site.uses, reason)


def _floor_problem(site: StepUse, lock: Lock) -> str | None:
    if site.uses.startswith("docker://"):
        return None
    form = unsupported_form(site)
    if form is not None:
        return f"forma sem runtime verificável — {form}"
    entry = lock.get(site.uses)
    if entry is None:
        return (
            f"runtime desconhecido: ref fora de {LOCK_PATH.name} — mesmo conserto do "
            f"action-inputs, rode `{REFRESH_CMD}`"
        )
    if entry.runs_using not in RUNTIME_FLOOR:
        return f"runs.using={entry.runs_using!r} fora do piso {sorted(RUNTIME_FLOOR)} ({EMENDA})"
    return None


def check_runtime_floor(sites: list[StepUse], lock: Lock) -> list[Violation]:
    """Todo workflow: runtime que o mantenedor não testou quebra calado no nightly/security."""
    found = ((site, _floor_problem(site, lock)) for site in sites)
    return [_violation(site, reason) for site, reason in found if reason]


def _required_problem(site: StepUse, lock: Lock, admitted: set[str]) -> str | None:
    """Forma não suportada, ref fora do lock e node<24 já reprovam no piso: aqui só o que é de required."""
    if site.uses.startswith("docker://"):
        return "`docker://` vedado em job required (ADR-320 §Emenda 2026-08-03)"
    if unsupported_form(site) is not None:
        return None
    if _action_name(site.uses) not in admitted:
        return f"não registrada em {REGISTRY_PATH.name}"
    entry = lock.get(site.uses)
    if entry is None or entry.runs_using not in RUNTIME_FLOOR - REQUIRED_RUNS_USING:
        return None
    return f"runs.using={entry.runs_using!r} vedado em job required — só {sorted(REQUIRED_RUNS_USING)} ({EMENDA})"


def _required_sites(sites: list[StepUse], registry: dict) -> list[StepUse]:
    required = registry["required_jobs"]
    return [site for site in sites if site.job in (required.get(site.workflow) or [])]


def check_required(sites: list[StepUse], lock: Lock, registry: dict) -> list[Violation]:
    admitted = set(registry["actions"])
    required = _required_sites(sites, registry)
    found = ((site, _required_problem(site, lock, admitted)) for site in required)
    return [_violation(site, reason) for site, reason in found if reason]


def check_registry_shape(registry: dict) -> list[Violation]:
    """O registro é só política: fato de runtime ali vira segunda fonte, que diverge do lock."""
    problems = []
    unknown = sorted(set(registry) - REGISTRY_KEYS)
    if unknown:
        problems.append(
            f"chave(s) de topo desconhecida(s) {unknown}; esperado {sorted(REGISTRY_KEYS)}"
        )
    actions = registry.get("actions")
    if not isinstance(actions, list) or not all(isinstance(name, str) for name in actions):
        problems.append(
            "`actions` deve ser lista de nomes `owner/repo` (política); fato como "
            f"runs_using vive em {LOCK_PATH.name} — veio {actions!r:.120}"
        )
    return [Violation(REGISTRY_PATH.name, "", "", problem) for problem in problems]


def _job_needs(job: dict) -> list[str]:
    needs = job.get("needs") or []
    return [needs] if isinstance(needs, str) else list(needs)


def required_closure(workflow_path: Path, root: str) -> set[str]:
    """Fecho transitivo de `needs:` a partir do agregador — o que o Ruleset de fato exige."""
    jobs = yaml.safe_load(workflow_path.read_text(encoding="utf-8")).get("jobs") or {}
    closure: set[str] = set()
    pending = [root]
    while pending:
        name = pending.pop()
        if name not in closure:
            closure.add(name)
            pending.extend(_job_needs(jobs.get(name) or {}))
    return closure


def check_closure_declared(registry: dict) -> list[Violation]:
    """Job no fecho do agregador e fora de `required_jobs` passaria calado por `check_required`."""
    violations: list[Violation] = []
    for workflow_file, root in CLOSURE_ROOTS.items():
        declared = set(registry["required_jobs"].get(workflow_file) or [])
        closure = required_closure(WORKFLOW_DIR / workflow_file, root)
        violations.extend(
            Violation(
                workflow_file, job, "", "no fecho `needs:` do agregador mas fora de required_jobs"
            )
            for job in sorted(closure - declared)
        )
    return violations


def check_all(registry: dict, lock: Lock, sites: list[StepUse]) -> list[Violation]:
    shape = check_registry_shape(registry)
    if shape:
        return shape
    return (
        check_closure_declared(registry)
        + check_required(sites, lock, registry)
        + check_runtime_floor(sites, lock)
    )


def report(violations: list[Violation]) -> int:
    if not violations:
        print("✓ fecho required declarado; runtime de toda action conferido no lock.")
        return 0
    print(f"✗ {len(violations)} violação(ões) de runtime de action:\n")
    for violation in violations:
        print(f"  {violation.format()}")
    print(
        "\nJob fora de required_jobs: declare-o em .github/third-party-actions.yml. Action "
        "nova em job required: rode o refresh, leia o runs_using no lock e só então admita "
        "o nome ali; docker ou composite não entram — mova o job para fora do fecho ou "
        "troque por script inline (cabeçalho do registro)."
    )
    return 1


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    return report(check_all(load_registry(), load_lock(), collect_step_uses(WORKFLOW_DIR)))


if __name__ == "__main__":
    sys.exit(main())
