#!/usr/bin/env python3
"""Responde 'posso pegar esta lane?' cruzando frontmatter com ocupação viva."""
# Por que existe: o SPRINT_CURRENT.md deriva do frontmatter, e `status` NÃO TEM
# ESCRITOR no pickup. Uma sessão que abre worktree e ainda não commitou é
# invisível a `git for-each-ref`, a `gh pr list` e ao SPRINT_CURRENT — os três
# lugares onde o protocolo do CLAUDE.md manda olhar.
#
# Caso de origem, medido em 2026-08-13: a A40.l35 estava `open` no frontmatter e
# no SPRINT_CURRENT enquanto uma sessão viva trabalhava nela há 2h num worktree,
# com 20+ arquivos modificados, DUAS lanes novas (l61, l62) e uma ADR nova (387)
# — nada commitado, nada pushado, zero PR. Quem lesse a superfície canônica
# pegaria a lane e colidiria; quem alocasse "próximo id de ADR livre" tomaria o
# 387. Só `git worktree list` + leitura DENTRO de cada worktree revela.
#
# Barato de propósito (~80 tokens de saída, precedente ADR-281): a alternativa é
# reler o _README da sprint e os arquivos de lane, ~40k tokens que respondem pior.

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, NamedTuple

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
TERMINAL_STATUS: frozenset[str] = frozenset({"shipped", "cancelled"})
WIKILINK_TARGET_RE = re.compile(r"^\[\[([^\]|#]+)")


class Occupancy(NamedTuple):
    """Sinal de ocupação com a fonte que o produziu — sinal sem fonte não é acionável."""

    source: str
    detail: str


def _git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}


def _lane_files(docs_root: Path) -> Iterable[Path]:
    return sorted(docs_root.glob("sprint/*/lanes/*.md"))


def collect_lanes(docs_root: Path) -> dict[str, dict[str, Any]]:
    """Mapa id → frontmatter de toda nota `type: lane`."""
    lanes: dict[str, dict[str, Any]] = {}
    for path in _lane_files(docs_root):
        front = _frontmatter(path)
        if front.get("type") == "lane" and front.get("id"):
            front["_path"] = path
            lanes[str(front["id"])] = front
    return lanes


def _worktree_paths() -> list[Path]:
    """Worktrees do clone — inclui os que nenhuma branch remota revela."""
    out = _git("worktree", "list", "--porcelain")
    return [Path(line[9:]) for line in out.splitlines() if line.startswith("worktree ")]


def _slug_of(lane_id: str, front: dict[str, Any]) -> str:
    declared = front.get("branch_slug")
    if declared:
        return str(declared)
    return lane_id.lower().replace(".", "-")


def _short_id(lane_id: str) -> str:
    """`A40.l35` → `a40-l35` — o prefixo que branches e arquivos de lane usam."""
    return lane_id.lower().replace(".", "-")


def _refs_mentioning(token: str) -> list[Occupancy]:
    out = _git("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
    hits = [ref for ref in out.splitlines() if token in ref.lower()]
    return [Occupancy("branch", ref) for ref in hits]


def _worktrees_mentioning(token: str) -> list[Occupancy]:
    """Worktree cujo path OU branch cita a lane — pega sessão sem nenhum commit."""
    signals: list[Occupancy] = []
    for path in _worktree_paths():
        branch = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=path).strip()
        if token in path.name.lower() or token in branch.lower():
            dirty = len([ln for ln in _git("status", "--short", cwd=path).splitlines() if ln])
            signals.append(Occupancy("worktree", f"{path.name} [{branch}] · {dirty} arq. sujos"))
    return signals


# Sinal que nenhum comando do protocolo vigente enxerga: a sessão da A40.l35
# criou A40.l61 e A40.l62 como arquivos não-commitados dentro do próprio
# worktree, e as duas eram invisíveis ao vault inteiro.
def _uncommitted_lane_files(lane_id: str) -> list[Occupancy]:
    """Arquivo de lane que existe só dentro de outro worktree, sem commit."""
    signals: list[Occupancy] = []
    token = _short_id(lane_id)
    for path in _worktree_paths():
        lanes_dir = path / "docs" / "sprint"
        if not lanes_dir.exists():
            continue
        untracked = _git("ls-files", "--others", "--exclude-standard", "docs/sprint", cwd=path)
        hits = [ln for ln in untracked.splitlines() if token in ln.lower()]
        signals.extend(Occupancy("arquivo não-commitado", f"{path.name}: {h}") for h in hits)
    return signals


def _pending_deps(front: dict[str, Any], lanes: dict[str, dict[str, Any]]) -> list[str]:
    pending: list[str] = []
    for raw in front.get("depends_on") or []:
        match = WIKILINK_TARGET_RE.match(str(raw))
        if not match:
            continue
        dep_id = match.group(1).strip()
        dep = lanes.get(dep_id)
        if dep is not None and dep.get("status") not in TERMINAL_STATUS:
            pending.append(f"{dep_id} ({dep.get('status')})")
    return pending


def occupancy_signals(lane_id: str, front: dict[str, Any]) -> list[Occupancy]:
    """Todos os sinais de que alguém já está na lane, do mais barato ao mais fundo."""
    tokens = {_short_id(lane_id), _slug_of(lane_id, front).lower()}
    signals: list[Occupancy] = []
    for token in sorted(tokens):
        signals.extend(_refs_mentioning(token))
        signals.extend(_worktrees_mentioning(token))
    signals.extend(_uncommitted_lane_files(lane_id))
    return list(dict.fromkeys(signals))


def _verdict(front: dict[str, Any], pending: list[str], signals: list[Occupancy]) -> str:
    if signals:
        return "OCUPADA — não pegue sem falar com quem está nela"
    if front.get("status") in TERMINAL_STATUS:
        return f"TERMINAL ({front.get('status')}) — nada a pegar"
    if front.get("status") == "planned":
        return "NÃO LIBERADA — `planned` é liberação por-lane, decisão do dono"
    if pending and front.get("partial_delivery") is not True:
        return f"BLOQUEADA — dep pendente: {', '.join(pending)}"
    if pending:
        return f"PEGÁVEL COM AMARRA PARCIAL — dep pendente: {', '.join(pending)}"
    return "LIVRE"


# §Pendência 13 da A40 (8 renumerações de id numa sessão): `ls` local mede o
# teto errado enquanto alguém segura o id numa branch ou num worktree.
def _report_unknown(lane_id: str) -> tuple[str, int]:
    """Id ausente da vault local ainda pode estar TOMADO por outra sessão."""
    signals = occupancy_signals(lane_id, {})
    if not signals:
        return (f"{lane_id}: não existe no vault e nenhum sinal de ocupação — id livre.", 2)
    out = [f"{lane_id}: NÃO existe na vault local, mas o id está TOMADO — não realoque."]
    out.extend(f"  ocupação [{s.source}]: {s.detail}" for s in signals)
    return ("\n".join(out), 1)


def report(lane_id: str, lanes: dict[str, dict[str, Any]]) -> tuple[str, int]:
    """Linhas do parecer + exit code (0 = livre/parcial, 1 = não pegável)."""
    front = lanes.get(lane_id)
    if front is None:
        return _report_unknown(lane_id)
    pending = _pending_deps(front, lanes)
    signals = occupancy_signals(lane_id, front)
    verdict = _verdict(front, pending, signals)
    out = [
        f"{lane_id} · status `{front.get('status')}` · {front.get('priority', 's/ prioridade')}",
        f"  {front.get('title', '')}",
        f"  veredito: {verdict}",
    ]
    out.extend(f"  ocupação [{s.source}]: {s.detail}" for s in signals)
    return ("\n".join(out), 0 if verdict.startswith(("LIVRE", "PEGÁVEL")) else 1)


def _sprint_of(front: dict[str, Any]) -> str:
    return str(front.get("sprint") or "")


def _scan(lanes: dict[str, dict[str, Any]], sprint: str) -> tuple[str, int]:
    """Varre uma sprint inteira e lista só o que é acionável."""
    rows = [lid for lid, f in sorted(lanes.items()) if _sprint_of(f) == sprint]
    if not rows:
        return (f"Nenhuma lane com sprint `{sprint}`.", 2)
    blocks = [report(lid, lanes)[0] for lid in rows]
    return ("\n\n".join(blocks), 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lane", nargs="?", help="id da lane, ex.: A40.l35")
    parser.add_argument("--sprint", help="varre todas as lanes de uma sprint, ex.: A40")
    args = parser.parse_args(argv)
    lanes = collect_lanes(DOCS)
    if args.sprint:
        text, code = _scan(lanes, args.sprint)
    elif args.lane:
        text, code = report(args.lane, lanes)
    else:
        parser.error("informe uma lane ou --sprint")
    print(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
