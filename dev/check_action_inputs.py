#!/usr/bin/env python3
"""Reprova `with:` com input que a action não declara no ref pinado (ADR-320 §Emenda 2026-10-09): o runner só avisa `Unexpected input(s)` e segue sem o efeito — o `exempt-pr-authors` do stale.yml nunca valeu e o stale fechou 8 PRs do Dependabot. Gate 100% offline contra `.github/actions.lock.yml`; rede só em `dev/refresh_actions_lock.py`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
LOCK_PATH = REPO_ROOT / ".github" / "actions.lock.yml"
REFRESH_CMD = "python3 dev/refresh_actions_lock.py"
# O runner aceita estes dois sem declaração em action `runs.using: docker*`.
DOCKER_IMPLICIT_INPUTS = frozenset({"args", "entrypoint"})
LOCK_HEADER = f"""\
# GERADO por `{REFRESH_CMD}` — não edite à mão (ADR-320 §Emenda 2026-10-09).
#
# FATOS lidos do action.yml de cada ref em uso. A chave é o `uses:` exato de um
# step de workflow. O gate `dev/check_action_inputs.py` é offline e reprova
# `with:` com chave fora de `inputs` ou dentro de `deprecated_inputs`. POLÍTICA
# (o que pode entrar em job required) vive à mão em .github/third-party-actions.yml.
#
# Bump de action (Dependabot ou manual) troca a chave: rode `{REFRESH_CMD}`
# na mesma branch. Ele busca o ref novo, relê as tags e poda o ref velho.
"""


@dataclass(frozen=True)
class StepUse:
    """Um `uses:` de workflow com as chaves do seu `with:`; `job_level` marca reusable workflow."""

    workflow: str
    job: str
    step: str
    uses: str
    with_keys: tuple[str, ...] = ()
    job_level: bool = False

    def where(self) -> str:
        return f"{self.workflow}::{self.job} [{self.step}] {self.uses}"


@dataclass(frozen=True)
class Violation:
    """Achado do gate, já com o valor ofensor e o shape esperado."""

    where: str
    reason: str

    def format(self) -> str:
        return f"{self.where} — {self.reason}"


@dataclass(frozen=True)
class LockEntry:
    """O que o action.yml de um ref declara; `resolved_sha` só existe para ref de tag."""

    runs_using: str
    inputs: tuple[str, ...]
    deprecated_inputs: tuple[str, ...] = ()
    resolved_sha: str | None = field(default=None)

    def accepted_inputs(self) -> frozenset[str]:
        """Em minúsculas: o runner compara com `StringComparer.OrdinalIgnoreCase`."""
        declared = {name.lower() for name in self.inputs}
        implicit = DOCKER_IMPLICIT_INPUTS if self.runs_using.startswith("docker") else frozenset()
        return frozenset(declared | implicit)


Lock = dict[str, LockEntry]


def _step_label(step: dict, index: int) -> str:
    return str(step.get("name") or step.get("id") or f"step #{index}")


def _step_use(workflow: str, job_name: str, index: int, step: dict) -> StepUse:
    keys = tuple(str(key) for key in (step.get("with") or {}))
    return StepUse(workflow, job_name, _step_label(step, index), str(step["uses"]), keys)


def _job_sites(workflow: str, job_name: str, job: dict) -> Iterator[StepUse]:
    if job.get("uses"):
        keys = tuple(str(key) for key in (job.get("with") or {}))
        yield StepUse(workflow, job_name, "job", str(job["uses"]), keys, job_level=True)
    steps = enumerate(job.get("steps") or [])
    yield from (_step_use(workflow, job_name, i, step) for i, step in steps if step.get("uses"))


def collect_step_uses(workflow_dir: Path = WORKFLOW_DIR) -> list[StepUse]:
    paths = sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")])
    sites: list[StepUse] = []
    for path in paths:
        jobs = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("jobs") or {}
        for job_name, job in jobs.items():
            sites.extend(_job_sites(path.name, job_name, job or {}))
    return sites


def unsupported_form(site: StepUse) -> str | None:
    """Forma que o gate não sabe verificar reprova em vez de passar calada — calar é a classe do incidente."""
    if site.job_level:
        return "`uses:` de job (reusable workflow): os inputs vivem em `on.workflow_call`"
    if site.uses.startswith("./"):
        return "action local: o gate não lê o action.yml do disco nem os steps dela"
    if site.uses.startswith("docker://"):
        return "`docker://`: o runner não valida inputs dessa forma"
    if "@" not in site.uses:
        return "`uses:` sem `@ref`"
    return None


def remote_uses(sites: list[StepUse]) -> list[str]:
    """Universo do lock: todo `uses:` de step em forma suportada, ordenado e sem repetição."""
    return sorted({site.uses for site in sites if unsupported_form(site) is None})


def load_lock(path: Path = LOCK_PATH) -> Lock:
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
    return {uses: _entry_from_yaml(raw) for uses, raw in (doc or {}).items()}


def _entry_from_yaml(raw: dict) -> LockEntry:
    return LockEntry(
        runs_using=str(raw["runs_using"]),
        inputs=tuple(raw.get("inputs") or ()),
        deprecated_inputs=tuple(raw.get("deprecated_inputs") or ()),
        resolved_sha=raw.get("resolved_sha"),
    )


def _entry_to_yaml(entry: LockEntry) -> dict:
    raw: dict = {"runs_using": entry.runs_using, "inputs": list(entry.inputs)}
    if entry.deprecated_inputs:
        raw["deprecated_inputs"] = list(entry.deprecated_inputs)
    if entry.resolved_sha:
        raw["resolved_sha"] = entry.resolved_sha
    return raw


def render_lock(lock: Lock) -> str:
    body = {uses: _entry_to_yaml(entry) for uses, entry in sorted(lock.items())}
    return LOCK_HEADER + "\n" + yaml.safe_dump(body, sort_keys=True, default_flow_style=False)


def _missing_entry(site: StepUse) -> Violation:
    return Violation(
        site.where(),
        f"ref fora de {LOCK_PATH.name}; inputs não verificáveis — rode `{REFRESH_CMD}` e "
        "commite o lock na mesma branch (PR do Dependabot: o procedimento de BEHIND "
        "está na entrada `github-actions` do .github/dependabot.yml)",
    )


def _key_problem(key: str, entry: LockEntry) -> str | None:
    """Deprecado reprova também: aviso que não bloqueia é o próprio incidente, um bump adiante."""
    accepted = entry.accepted_inputs()
    if key.lower() not in accepted:
        return f"input {key!r} não existe neste ref; inputs válidos: {sorted(accepted)}"
    if key.lower() in {name.lower() for name in entry.deprecated_inputs}:
        return f"input {key!r} está deprecado neste ref; migre no bump"
    return None


def check_site(site: StepUse, lock: Lock) -> list[Violation]:
    reason = unsupported_form(site)
    if reason is not None:
        return [Violation(site.where(), f"forma não suportada pelo gate — {reason}")]
    entry = lock.get(site.uses)
    if entry is None:
        return [_missing_entry(site)]
    problems = (_key_problem(key, entry) for key in site.with_keys)
    return [Violation(site.where(), problem) for problem in problems if problem]


def check_orphans(sites: list[StepUse], lock: Lock) -> list[Violation]:
    """Entrada que nenhum step usa é ref velho de um bump: o lock espelha o que está em uso, nada mais."""
    return [
        Violation(
            f"{LOCK_PATH.name}::{uses}", f"nenhum workflow usa este ref — rode `{REFRESH_CMD}`"
        )
        for uses in sorted(set(lock) - set(remote_uses(sites)))
    ]


def check_all(sites: list[StepUse], lock: Lock) -> list[Violation]:
    return check_orphans(sites, lock) + [v for site in sites for v in check_site(site, lock)]


def report(violations: list[Violation]) -> int:
    if not violations:
        print("✓ todo `with:` de `uses:` casa com os inputs do ref pinado.")
        return 0
    print(f"✗ {len(violations)} violação(ões) de input de action:\n")
    for violation in violations:
        print(f"  {violation.format()}")
    print(
        "\nInput inexistente é ignorado pelo runner, que só deixa um warning no log: "
        "corrija o nome ou remova a chave."
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    return report(check_all(collect_step_uses(), load_lock()))


if __name__ == "__main__":
    sys.exit(main())
