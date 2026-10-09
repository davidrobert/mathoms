#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-commit hook: requirements.lock satisfaz os *.in (ADR-254)."""

# Falha se um pacote direto declarado em requirements.in/backend/requirements.in
# está ausente do lock combinado requirements.lock, OU se a versão pinada no lock
# não satisfaz o specifier do .in. Só a presença de nome deixava passar o PR do
# Dependabot que sobe o piso sem regenerar o lock: o CI instala do lock e fica
# verde (5 de 8 PRs pip mergeados em 2026-08-25/31 deixaram o .in acima do lock
# até o #2046). NÃO regenera o lock — isso exige container linux/amd64 (runbook
# docs/reference/runbooks/python_dependencies.md); só detecta drift. Roda com
# pass_filenames: false (conjunto fixo).
#
# Família opentelemetry-*: os pisos `>=` de cada trilha (core 1.x, contrib
# 0.Xb0) têm que ser iguais. A família é acoplada por `==` (sdk 1.Y ⇒
# api==1.Y; instrumentation 0.Xb0 ⇒ semantic-conventions==0.Xb0), então um
# membro sozinho com piso novo pede uma combinação que o lock não tem — e o
# Dependabot propõe um membro por PR (grupos pip nunca agruparam neste repo).

from __future__ import annotations

import re
import sys
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_FILES = (REPO_ROOT / "requirements.in", REPO_ROOT / "backend" / "requirements.in")
LOCK_FILE = REPO_ROOT / "requirements.lock"

_LOCK_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s\\;]+)")
_OTEL_PREFIX = "opentelemetry-"


def _parse_requirement(path: Path, line: str) -> Requirement:
    try:
        return Requirement(line)
    except InvalidRequirement as exc:
        raise SystemExit(f"[lockfile-sync] {path.name}: linha inválida {line!r} ({exc})") from exc


def declared_requirements(path: Path) -> list[Requirement]:
    reqs: list[Requirement] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            reqs.append(_parse_requirement(path, line))
    return reqs


def locked_versions(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = _LOCK_PIN.match(raw)
        if m:
            pins[canonicalize_name(m.group(1))] = m.group(2)
    return pins


def _lock_violation(req: Requirement, pins: dict[str, str]) -> str | None:
    pinned = pins.get(canonicalize_name(req.name))
    if pinned is None:
        return f"{req.name}: ausente do lock"
    if not req.specifier.contains(pinned, prereleases=True):
        return f"{req.name}: o lock pina {pinned}, o .in pede {req.specifier}"
    return None


def lock_violations(declared: list[Requirement], pins: dict[str, str]) -> list[str]:
    return [v for req in declared if (v := _lock_violation(req, pins)) is not None]


def _floor(req: Requirement) -> str | None:
    floors = [spec.version for spec in req.specifier if spec.operator == ">="]
    return floors[0] if len(floors) == 1 else None


def otel_floors(declared: list[Requirement]) -> dict[str, str | None]:
    return {
        canonicalize_name(req.name): _floor(req)
        for req in declared
        if canonicalize_name(req.name).startswith(_OTEL_PREFIX)
    }


def otel_track(floor: str) -> str:
    return "0.Xb0" if Version(floor).major == 0 else "1.x"


def otel_floor_violations(declared: list[Requirement]) -> list[str]:
    floors = otel_floors(declared)
    violations = [f"{name}: esperado um único piso `>=`" for name, f in floors.items() if f is None]
    tracks: dict[str, dict[str, str]] = {}
    for name, floor in floors.items():
        if floor is not None:
            tracks.setdefault(otel_track(floor), {})[name] = floor
    return violations + [
        f"opentelemetry-* {track}: pisos distintos {by_name}; esperado um piso só "
        "por trilha (o pinado no lock) — a família é acoplada por `==`"
        for track, by_name in sorted(tracks.items())
        if len({Version(v) for v in by_name.values()}) > 1
    ]


def _missing_inputs() -> list[Path]:
    return [path for path in (*IN_FILES, LOCK_FILE) if not path.exists()]


def _all_violations() -> list[str]:
    pins = locked_versions(LOCK_FILE)
    declared = {f.relative_to(REPO_ROOT): declared_requirements(f) for f in IN_FILES}
    unsatisfied = [
        f"{path} · {violation}"
        for path, reqs in declared.items()
        for violation in lock_violations(reqs, pins)
    ]
    return unsatisfied + otel_floor_violations([r for reqs in declared.values() for r in reqs])


def main() -> int:
    missing = _missing_inputs()
    if missing:
        print(f"[lockfile-sync] esperado e não encontrado: {', '.join(map(str, missing))}")
        return 1
    violations = _all_violations()
    if not violations:
        return 0
    print("[lockfile-sync] requirements.lock e *.in inconsistentes:")
    print("\n".join(f"  - {v}" for v in violations))
    print(
        "→ docs/reference/runbooks/python_dependencies.md: Tarefa 1 (regenerar o lock) "
        "· §Família opentelemetry (pisos da família)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
