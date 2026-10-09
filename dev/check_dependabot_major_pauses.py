#!/usr/bin/env python3
"""Pre-commit: major npm pausado no `dependabot.yml` só enquanto um peer do lock o barra (ADR-449).

Major bloqueado por peer não fica em PR aberto: o PR do Dependabot só sabe ficar
vermelho e ocupar vaga. Ele vira um `ignore` versionado (`versions: [">=N"]`),
com data e gatilho no comentário, e uma linha em `PAUSES`. O gate reprova:

1. `ignore` de major npm sem pausa registrada, ou pausa sem `ignore`, por
   igualdade de conjunto (app, dependência, major);
2. pausa cujo gatilho disparou: nenhuma entrada do `<app>/package-lock.json`
   declara `peerDependencies[peer]` que exclua o major. O peer opcional conta,
   porque é combinação fora do suporte do vizinho, mesmo que o npm 11 a aceite;
3. pausa vencida: `--today` passou do `review_by`. Renovar é um commit com
   justificativa, não um silêncio.

Roda no Lint (`--all-files`), e por isso o gatilho aparece no PR do Dependabot que
libera o peer. Esse PR fica vermelho até um PR humano levar o bump junto com a
remoção do `ignore` (o Dependabot fecha o dele sozinho). Um teste em `tests/`
não serviria: o `pipeline-tests` não roda em PR que só muda `<app>/package*.json`.

Limites: o range npm é avaliado por um subconjunto do semver (`^ ~ >= > <= <`,
`x`/`*`, `||`). Hyphen range reprova (fail-closed). Prerelease conta como a
versão base.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
_INF = (10**9, 0, 0)
_ZERO = (0, 0, 0)
_WARN_DAYS = 14
_OP_SPACE_RE = re.compile(r"(>=|<=|>|<|=)\s+")
_TOKEN_RE = re.compile(
    r"^(?P<op>\^|~|>=|<=|>|<|=)?v?(?P<major>\d+|[xX*])"
    r"(?:\.(?P<minor>\d+|[xX*]))?(?:\.(?P<patch>\d+|[xX*]))?(?:[-+][0-9A-Za-z.+-]*)?$"
)
_MAJOR_IGNORE_RE = re.compile(r"^>=\s*(\d+)(?:\.0){0,2}$")

Version = tuple[int, int, int]


@dataclass(frozen=True)
class MajorPause:
    app: str
    deps: tuple[str, ...]
    major: int
    peer: str
    since: dt.date
    review_by: dt.date
    closed_prs: str


PAUSES: tuple[MajorPause, ...] = (
    MajorPause(
        "frontend",
        ("eslint", "@eslint/js"),
        10,
        "eslint",
        dt.date(2026, 10, 9),
        dt.date(2026, 11, 30),
        "#2232",
    ),
    MajorPause(
        "frontend-ops",
        ("eslint", "@eslint/js"),
        10,
        "eslint",
        dt.date(2026, 10, 9),
        dt.date(2026, 11, 30),
        "#2230 #2181",
    ),
    MajorPause(
        "frontend",
        ("typescript",),
        7,
        "typescript",
        dt.date(2026, 10, 9),
        dt.date(2027, 1, 31),
        "#2132",
    ),
    MajorPause(
        "frontend-ops",
        ("typescript",),
        7,
        "typescript",
        dt.date(2026, 10, 9),
        dt.date(2027, 1, 31),
        "#2180",
    ),
    MajorPause("frontend", ("msw",), 3, "msw", dt.date(2026, 10, 9), dt.date(2027, 1, 31), "#2187"),
)


def range_admits_major(spec: str, major: int) -> bool:
    """Algum `major.x.y` satisfaz o range npm `spec`?"""
    return any(_set_admits_major(part.strip(), major) for part in spec.split("||"))


def _set_admits_major(comparator_set: str, major: int) -> bool:
    if " - " in comparator_set:
        raise ValueError(f"hyphen range fora do subconjunto suportado: {comparator_set!r}")
    low, high = (major, 0, 0), (major + 1, 0, 0)
    for token in _OP_SPACE_RE.sub(r"\1", comparator_set).split():
        token_low, token_high = _token_bounds(token)
        low, high = max(low, token_low), min(high, token_high)
    return low < high


def _token_bounds(token: str) -> tuple[Version, Version]:
    match = _TOKEN_RE.match(token)
    if match is None:
        raise ValueError(f"comparador npm não suportado: {token!r}")
    parts = [match.group(k) for k in ("major", "minor", "patch")]
    numbers = [int(p) if p and p.isdigit() else None for p in parts]
    if numbers[0] is None:
        return _ZERO, _INF
    return _bounds_for(match.group("op") or "=", numbers)


def _bounds_for(op: str, numbers: list[int | None]) -> tuple[Version, Version]:
    base: Version = (numbers[0] or 0, numbers[1] or 0, numbers[2] or 0)
    after = _next_after(numbers)
    if op == ">=":
        return base, _INF
    if op == ">":
        return after, _INF
    if op == "<":
        return _ZERO, base
    if op == "<=":
        return _ZERO, after
    if op == "~":
        return base, after if numbers[1] is None else (base[0], base[1] + 1, 0)
    if op == "^":
        return base, _caret_high(base, numbers)
    return base, after


def _next_after(numbers: list[int | None]) -> Version:
    major, minor, patch = numbers
    if minor is None:
        return (major + 1, 0, 0)
    if patch is None:
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def _caret_high(base: Version, numbers: list[int | None]) -> Version:
    if base[0] > 0 or numbers[1] is None:
        return (base[0] + 1, 0, 0)
    if base[1] > 0 or numbers[2] is None:
        return (0, base[1] + 1, 0)
    return (0, 0, base[2] + 1)


def peer_blockers(lock: dict, peer: str, major: int) -> list[str]:
    """Entradas do lock cujo `peerDependencies[peer]` exclui o major."""
    blockers = []
    for key, entry in lock.get("packages", {}).items():
        spec = (entry.get("peerDependencies") or {}).get(peer)
        if key and spec is not None and not range_admits_major(spec, major):
            name = key.rsplit("node_modules/", 1)[-1]
            blockers.append(f"{name}@{entry.get('version')} (peer {peer} {spec!r})")
    return sorted(blockers)


def yml_major_ignores(config: dict) -> tuple[set[tuple[str, str, int]], list[str]]:
    """(app, dep, major) de todo `ignore` `>=N` de entrada npm, e as formas fora do padrão."""
    found: set[tuple[str, str, int]] = set()
    unsupported: list[str] = []
    for entry in config.get("updates", []):
        if entry.get("package-ecosystem") == "npm":
            _collect_entry_ignores(entry, found, unsupported)
    return found, unsupported


def _collect_entry_ignores(entry: dict, found: set, unsupported: list[str]) -> None:
    app = entry["directory"].strip("/")
    for rule in entry.get("ignore", []):
        parsed = _parse_major_ignore(rule)
        if parsed is None:
            unsupported.append(f"{app}: {rule}")
        else:
            found.add((app, rule["dependency-name"], parsed))


def _parse_major_ignore(rule: dict) -> int | None:
    versions = rule.get("versions") or []
    if set(rule) != {"dependency-name", "versions"} or len(versions) != 1:
        return None
    match = _MAJOR_IGNORE_RE.match(str(versions[0]).strip())
    return int(match.group(1)) if match else None


def registered_ignores(pauses: tuple[MajorPause, ...]) -> set[tuple[str, str, int]]:
    return {(p.app, dep, p.major) for p in pauses for dep in p.deps}


def check_registry(config: dict, pauses: tuple[MajorPause, ...]) -> list[str]:
    found, unsupported = yml_major_ignores(config)
    expected = registered_ignores(pauses)
    failures = [f"ignore npm fora da forma `versions: ['>=N']`: {u}" for u in unsupported]
    for app, dep, major in sorted(found - expected):
        failures.append(f"{app}: ignore de {dep} >={major} sem pausa em PAUSES (gatilho + prazo)")
    for app, dep, major in sorted(expected - found):
        failures.append(f"{app}: pausa de {dep} >={major} em PAUSES sem ignore no dependabot.yml")
    return failures


def check_pause(repo: Path, pause: MajorPause, today: dt.date) -> list[str]:
    label = f"{pause.app}: pausa de {'/'.join(pause.deps)} {pause.major} ({pause.closed_prs})"
    failures = []
    lock = json.loads((repo / pause.app / "package-lock.json").read_text(encoding="utf-8"))
    if not peer_blockers(lock, pause.peer, pause.major):
        failures.append(
            f"{label}: gatilho disparou — nenhum pacote do lock barra {pause.peer} {pause.major}. "
            "Apague o ignore e a linha de PAUSES no mesmo PR do bump (ADR-449)."
        )
    if today > pause.review_by:
        failures.append(
            f"{label}: prazo {pause.review_by} vencido. Migre, ou renove o review_by "
            "com a justificativa no commit (ADR-449)."
        )
    elif (pause.review_by - today).days <= _WARN_DAYS:
        print(
            f"::warning::{label}: prazo {pause.review_by} em {(pause.review_by - today).days} dias"
        )
    return failures


def main(argv: list[str] | None = None, *, pauses: tuple[MajorPause, ...] = PAUSES) -> int:
    args = _parse_args(argv)
    config = yaml.safe_load((args.repo / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    failures = check_registry(config, pauses)
    for pause in pauses:
        failures.extend(check_pause(args.repo, pause, args.today))
    for failure in failures:
        print(f"🛑 {failure}", file=sys.stderr)
    return 1 if failures else 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
