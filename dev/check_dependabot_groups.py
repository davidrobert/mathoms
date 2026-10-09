#!/usr/bin/env python3
"""Pre-commit: todo padrão de grupo do `dependabot.yml` entrega dependência ao próprio grupo.

Em 2026-10-09 os grupos `eslint-and-types` e `vitest-and-test` do /frontend e o
`pytest` do pip estavam inertes. O updater loga "Skipping X for group 'G' -
belongs to more specific group 'patch-and-minor'" e manda tudo para o catch-all:
um grupo sem `patterns` vale 500, e um padrão com curinga vale ~100. O #2129
(vitest 3→5) saiu sozinho do grupo, sem o `@vitest/coverage-v8`, e ficou vermelho.

Este gate porta a regra do dependabot-core e a roda sobre as dependências
diretas dos manifests. Ele reprova três casos:

1. a dependência casa um padrão do grupo, mas o core a dá a outro grupo, mais
   específico;
2. o grupo recebe a dependência, mas um grupo anterior no yml a atende primeiro,
   porque o core processa na ordem do arquivo e marca a dependência como handled;
3. o padrão não casa nenhuma dependência direta. É o WARN "groups where no
   dependencies match" do updater, medido por padrão.

O porte vem de `updater/lib/dependabot/updater/pattern_specificity_calculator.rb`,
de `dependency_group_engine.rb#should_skip_due_to_specificity?` e de
`common/lib/wildcard_matcher.rb` (dependabot-core 4725d253, 2026-10-09).

Limites: o gate só lê npm (`<dir>/package.json`) e a entrada pip `/` (os dois
`.in` + `requirements-dev.txt`, sem o `pyproject.toml`). Docker e github-actions
ficam de fora. O core pode mudar a regra sem aviso, e o gate não lê o log real
do updater.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEPENDABOT_YML = REPO_ROOT / ".github" / "dependabot.yml"
PIP_ROOT_FILES = ("requirements.in", "backend/requirements.in", "requirements-dev.txt")

EXPLICIT_MEMBER_SCORE = 1000
EXACT_MATCH_SCORE = 1000
NO_WILDCARDS_SCORE = 500
NO_PATTERNS_SCORE = 500
WILDCARD_BASE_SCORE = 100
WILDCARD_PENALTY = 10
UNIVERSAL_WILDCARD_SCORE = 1
MINIMUM_SCORE = 1
LENGTH_BONUS_THRESHOLD = 5

PORTED_RULES = frozenset({"patterns", "exclude-patterns", "update-types", "applies-to"})
_REQUIREMENT_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
HINT = (
    "Para tornar o grupo efetivo, use nome exato (vence o catch-all), `update-types` "
    "disjunto do catch-all (modelo do actions-first-party-major) ou `exclude-patterns` "
    "no catch-all. Ou remova o grupo. Regra: docstring de dev/check_dependabot_groups.py."
)


def wildcard_match(pattern: str, name: str) -> bool:
    """Porte do `WildcardMatcher.match?`: `*` casa qualquer trecho, sem caixa."""
    regex = ".*".join(re.escape(part) for part in pattern.lower().split("*"))
    return re.fullmatch(regex, name.lower()) is not None


@dataclass(frozen=True)
class DependabotGroup:
    name: str
    patterns: tuple[str, ...] | None
    exclude_patterns: tuple[str, ...]
    update_types: frozenset[str] | None
    applies_to: str

    def excludes(self, dep: str) -> bool:
        return any(wildcard_match(pattern, dep) for pattern in self.exclude_patterns)

    def contains(self, dep: str) -> bool:
        if self.excludes(dep):
            return False
        return self.patterns is None or any(wildcard_match(p, dep) for p in self.patterns)

    def competes_with(self, other: DependabotGroup) -> bool:
        """`update-types` disjuntos são complementares, e `applies-to` separa o job."""
        if other is self or other.applies_to != self.applies_to:
            return False
        if self.update_types is None or other.update_types is None:
            return True
        return bool(self.update_types & other.update_types)


def parse_group(name: str, rules: dict[str, object]) -> DependabotGroup:
    unported = sorted(set(rules) - PORTED_RULES)
    if unported:
        raise ValueError(
            f"grupo '{name}': regra {unported} fora do porte, "
            f"esperado só {sorted(PORTED_RULES)}; porte a regra antes de usá-la"
        )
    patterns = rules.get("patterns")
    update_types = rules.get("update-types")
    return DependabotGroup(
        name=name,
        patterns=tuple(patterns) if patterns is not None else None,
        exclude_patterns=tuple(rules.get("exclude-patterns") or ()),
        update_types=frozenset(update_types) if update_types is not None else None,
        applies_to=str(rules.get("applies-to") or "version-updates"),
    )


def pattern_score(pattern: str, dep: str) -> int:
    if pattern == dep:
        return EXACT_MATCH_SCORE
    if pattern == "*":
        return UNIVERSAL_WILDCARD_SCORE
    wildcards = pattern.count("*")
    if wildcards == 0:
        return NO_WILDCARDS_SCORE
    bonus = max(len(pattern) - LENGTH_BONUS_THRESHOLD, 0)
    return max(WILDCARD_BASE_SCORE - wildcards * WILDCARD_PENALTY + bonus, MINIMUM_SCORE)


def group_score(group: DependabotGroup, dep: str, members: dict[str, list[str]]) -> int:
    if dep in members[group.name]:
        return EXPLICIT_MEMBER_SCORE
    if group.excludes(dep):
        return 0
    if group.patterns is None:
        return NO_PATTERNS_SCORE
    scores = [pattern_score(p, dep) for p in group.patterns if wildcard_match(p, dep)]
    return max(scores, default=0)


def more_specific_group(
    group: DependabotGroup,
    dep: str,
    groups: list[DependabotGroup],
    members: dict[str, list[str]],
) -> str | None:
    """Porte do `find_most_specific_group_name`: só grupo com `patterns` cede a dependência."""
    if group.patterns is None or group.excludes(dep):
        return None
    best = group_score(group, dep, members)
    if best >= EXPLICIT_MEMBER_SCORE:
        return None
    winner = None
    for other in groups:
        if not group.competes_with(other) or not other.contains(dep):
            continue
        score = group_score(other, dep, members)
        if score > best:
            best, winner = score, other.name
    return winner


def assign_members(
    groups: list[DependabotGroup], deps: list[str]
) -> tuple[dict[str, list[str]], list[tuple[str, str, str]]]:
    """Porte do `assign_dependencies_to_groups`: devolve membros e desvios (grupo, dep, vencedor)."""
    members: dict[str, list[str]] = {group.name: [] for group in groups}
    diverted: list[tuple[str, str, str]] = []
    for dep in deps:
        for group in groups:
            if not group.contains(dep):
                continue
            winner = more_specific_group(group, dep, groups, members)
            if winner:
                diverted.append((group.name, dep, winner))
                continue
            members[group.name].append(dep)
    return members, diverted


def shadowed_members(
    groups: list[DependabotGroup], members: dict[str, list[str]]
) -> list[tuple[str, str, str]]:
    """(grupo, dep, anterior): o anterior também a recebeu e é processado antes."""
    found = []
    for index, group in enumerate(groups):
        if group.patterns is None:
            continue
        for dep in members[group.name]:
            earlier = [
                h.name for h in groups[:index] if group.competes_with(h) and dep in members[h.name]
            ]
            found.extend((group.name, dep, name) for name in earlier[:1])
    return found


def dead_patterns(groups: list[DependabotGroup], deps: list[str]) -> list[tuple[str, str]]:
    return [
        (group.name, pattern)
        for group in groups
        for pattern in group.patterns or ()
        if not any(wildcard_match(pattern, dep) and not group.excludes(dep) for dep in deps)
    ]


def entry_violations(label: str, groups: list[DependabotGroup], deps: list[str]) -> list[str]:
    members, diverted = assign_members(groups, deps)
    lines = [
        f"{label} '{group}': '{dep}' casa o padrão, mas o core dá a dep a '{winner}' (mais específico)"
        for group, dep, winner in diverted
    ]
    lines += [
        f"{label} '{group}': '{dep}' é atendida antes por '{earlier}', que vem antes no yml"
        for group, dep, earlier in shadowed_members(groups, members)
    ]
    lines += [
        f"{label} '{group}': o padrão '{pattern}' não casa nenhuma dependência direta"
        for group, pattern in dead_patterns(groups, deps)
    ]
    return lines


def npm_dependencies(package_json: Path) -> list[str]:
    manifest = json.loads(package_json.read_text(encoding="utf-8"))
    sections = ("dependencies", "devDependencies", "optionalDependencies")
    return sorted({name for section in sections for name in manifest.get(section, {})})


def pip_dependencies(root: Path, files: tuple[str, ...] = PIP_ROOT_FILES) -> list[str]:
    """Nomes PEP 503 das linhas de requisito; `-r`/`-c` e comentários ficam de fora."""
    names = set()
    for relative in files:
        for raw in (root / relative).read_text(encoding="utf-8").splitlines():
            match = _REQUIREMENT_NAME.match(raw.split("#", 1)[0].strip())
            if match:
                names.add(re.sub(r"[-_.]+", "-", match.group(1)).lower())
    return sorted(names)


def entry_dependencies(entry: dict[str, object], root: Path) -> list[str] | None:
    ecosystem = entry["package-ecosystem"]
    directory = str(entry["directory"]).strip("/")
    if ecosystem == "npm":
        return npm_dependencies(root / directory / "package.json")
    if ecosystem == "pip" and directory == "":
        return pip_dependencies(root)
    return None


def config_violations(config: dict[str, object], root: Path) -> list[str]:
    found: list[str] = []
    for entry in config["updates"]:
        deps = entry_dependencies(entry, root)
        if deps is None:
            continue
        groups = [parse_group(name, rules) for name, rules in (entry.get("groups") or {}).items()]
        label = f"{entry['package-ecosystem']} {entry['directory']}"
        found += entry_violations(label, groups, deps)
    return found


def main() -> int:
    config = yaml.safe_load(DEPENDABOT_YML.read_text(encoding="utf-8"))
    try:
        found = config_violations(config, REPO_ROOT)
    except ValueError as error:
        print(f"dependabot-groups: {error}", file=sys.stderr)
        return 1
    if not found:
        return 0
    print("dependabot-groups: grupo que não recebe a dependência que promete:", file=sys.stderr)
    for line in found:
        print(f"  - {line}", file=sys.stderr)
    print(HINT, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
