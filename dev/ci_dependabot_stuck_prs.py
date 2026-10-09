"""PR do Dependabot parado: idade da CADEIA de substituição, não do PR. Consumido por
`dev/ci_dependabot_health.py` (sinal "PR parado" na issue `ops-dependabot-red`).

Limite declarado: a cadeia se quebra quando o Dependabot reestrutura a branch (dep
avulsa vira `multi-…` ou grupo) — subestima a idade, nunca superestima."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

PR_FIELDS = "number,url,headRefName,createdAt,closedAt,mergedAt"
PR_LIST_LIMIT = 1000
# Medido em 2026-10-09 sobre 99 PRs: o substituto nasce entre -50s e +6s do
# fechamento do antigo ("Superseded by #N"). 5 min de folga, sem cruzar run semanal.
SUPERSEDE_GAP = timedelta(minutes=5)
# Sufixo de versão (`next-16.4.0`, `litellm-gte-1.104.0`) ou hash de grupo
# (`patch-and-minor-5f4151c9e1`): o que sobra identifica a dep entre substituições.
BRANCH_SUFFIX = re.compile(r"-(?:[0-9a-f]{10}|v?\d[\w.+-]*)$")
# `multi-<hash>` junta deps diferentes sob o mesmo prefixo; sem o hash, PRs distintos
# fechados e abertos na mesma run virariam cadeia e a idade seria SUPERestimada.
MULTI_DEP = re.compile(r"multi-[0-9a-f]{10}")


@dataclass(frozen=True)
class DependabotPr:
    number: int
    url: str
    ecosystem: str
    directory: str | None
    key: str
    created_at: datetime
    closed_at: datetime | None
    merged: bool

    def entry_key(self) -> tuple[str, str | None]:
        return self.ecosystem, self.directory

    def same_chain(self, other: DependabotPr) -> bool:
        return (self.entry_key(), self.key) == (other.entry_key(), other.key)

    def open_at(self, moment: datetime) -> bool:
        return self.created_at <= moment and (self.closed_at is None or self.closed_at > moment)


@dataclass(frozen=True)
class StuckPr:
    pr: DependabotPr
    since: datetime


@dataclass(frozen=True)
class Occupancy:
    """Vagas da entrada. Security update tem limite próprio, mas conta aqui junto:
    o erro cai do lado barato (uma issue a mais)."""

    limit: int
    prs: tuple[DependabotPr, ...]

    def open_at(self, moment: datetime) -> int:
        return sum(pr.open_at(moment) for pr in self.prs)

    def open_now(self) -> int:
        return sum(pr.closed_at is None for pr in self.prs)

    def filled_since(self, moment: datetime) -> bool:
        """Lotou depois de `moment`: PR deixado aberto na triagem agora trava a entrada."""
        return self.open_now() >= self.limit > self.open_at(moment)


def split_branch(branch: str, dirs: Collection[str]) -> tuple[str, str | None, str]:
    """`dependabot/<eco>/<dir>/<dep>` → (eco, dir, dep); a raiz não tem segmento de dir."""
    _, ecosystem, rest = branch.split("/", 2)
    for directory in sorted(dirs, key=len, reverse=True):
        segment = directory.strip("/")
        if segment and rest.startswith(f"{segment}/"):
            return ecosystem, directory, rest.removeprefix(f"{segment}/")
    root = next((d for d in dirs if not d.strip("/")), None)
    return ecosystem, root, rest


def chain_key(dep: str) -> str:
    return dep if MULTI_DEP.fullmatch(dep) else BRANCH_SUFFIX.sub("", dep)


def parse_pr(raw: dict, dirs_by_ecosystem: Mapping[str, Collection[str]]) -> DependabotPr:
    ecosystem = raw["headRefName"].split("/")[1]
    eco, directory, dep = split_branch(raw["headRefName"], dirs_by_ecosystem.get(ecosystem, ()))
    closed = raw.get("closedAt")
    return DependabotPr(
        number=raw["number"],
        url=raw["url"],
        ecosystem=eco,
        directory=directory,
        key=chain_key(dep),
        created_at=datetime.fromisoformat(raw["createdAt"]),
        closed_at=datetime.fromisoformat(closed) if closed else None,
        merged=bool(raw.get("mergedAt")),
    )


def _superseded(start: datetime, pr: DependabotPr, prs: list[DependabotPr]) -> list[datetime]:
    return [
        q.created_at
        for q in prs
        if q.same_chain(pr)
        and q.closed_at is not None
        and not q.merged
        and q.created_at < start
        and abs(q.closed_at - start) <= SUPERSEDE_GAP
    ]


def chain_start(pr: DependabotPr, prs: list[DependabotPr]) -> datetime:
    """Criação do 1º PR da cadeia; merge interrompe a cadeia, fechamento sem merge não."""
    start = pr.created_at
    while predecessors := _superseded(start, pr, prs):
        start = min(predecessors)
    return start


def stuck_prs(prs: list[DependabotPr], now: datetime, max_age: timedelta) -> list[StuckPr]:
    open_prs = (pr for pr in prs if pr.closed_at is None)
    found = (StuckPr(pr, chain_start(pr, prs)) for pr in open_prs)
    return sorted((s for s in found if now - s.since > max_age), key=lambda s: s.since)


def _pr_list(gh: Callable[..., str], *filters: str) -> list[dict]:
    args = ("--author", "app/dependabot", "--limit", str(PR_LIST_LIMIT), "--json", PR_FIELDS)
    found = json.loads(gh("pr", "list", *args, *filters))
    if len(found) >= PR_LIST_LIMIT:
        raise ValueError(f"lista cortada em {PR_LIST_LIMIT} PRs ({' '.join(filters)})")
    return found


def fetch_dependabot_prs(gh: Callable[..., str], since: datetime) -> list[dict]:
    """Abertos de qualquer idade (o pior caso é o mais velho) + fechados desde `since`."""
    window = f"closed:>={since:%Y-%m-%d}"
    found = _pr_list(gh, "--state", "open") + _pr_list(gh, "--state", "closed", "--search", window)
    if not found:
        raise ValueError(f"0 PRs do Dependabot desde {since:%Y-%m-%d} — o token lê pull requests?")
    return found
