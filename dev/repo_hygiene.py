#!/usr/bin/env python3
"""Higiene do clone: relata o que acumula e, com `--apply`, remove só o recuperável.

Três coisas são removidas, nenhuma com perda de conteúdo:

- registro de worktree cujo diretório sumiu (`git worktree prune`);
- ref `origin/*` de branch já apagada no remoto (`git remote prune origin`);
- branch local `agent/*`/`claude/*` cujo conteúdo já está em `origin/main` e que
  nenhum worktree tem em checkout. "Entregue" é o predicado de
  `dev/_lane_branch_delivery.py` (ancestral ∨ patch-id do diff agregado): squash
  nunca deixa a branch ancestral, então `git branch --merged` não serve. Cada
  remoção grava a linha de restauração em `_scratch/`.

Duas são só relatadas, porque agir é decisão do dono: PRs do Dependabot (merge
publica) e o stash (a pilha é compartilhada entre worktrees — dropar pega o de
outra sessão).

Branch que não classifica é VIVA e fica: a que está a mais de `TETO_COMMITS` de
`origin/main` nem passa pelo patch-id. Sem `git fetch` — `origin/main` velho só
torna o veredito mais conservador.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, NamedTuple

try:  # script direto vs. import como `dev.*` (padrão de dev/lane_pickup.py)
    import _lane_branch_delivery as _delivery  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover
    from dev import _lane_branch_delivery as _delivery  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
BRANCH_NAMESPACES = ("refs/heads/agent", "refs/heads/claude")
DELETE_CHUNK = 100
_WOULD_PRUNE_RE = re.compile(r"\[would prune\] (\S+)")
# Exige `N.M` dos dois lados: digest de imagem (`4013ae0`) não é versão.
_VERSION_JUMP_RE = re.compile(r"from [^\d\s]*(\d+)\.\d\S* to [^\d\s]*(\d+)\.\d")

Classifier = Callable[[list[str]], tuple[list[str], list[str], list[str]]]


class LocalBranch(NamedTuple):
    name: str
    sha: str
    ahead: int
    behind: int


class DependabotPr(NamedTuple):
    number: int
    title: str
    age_days: int
    major: bool


@dataclass(frozen=True)
class BranchTriage:
    delivered: list[LocalBranch] = field(default_factory=list)
    checked_out: int = 0
    alive: int = 0
    beyond_cap: int = 0
    blind_reasons: list[str] = field(default_factory=list)


def _git(*args: str) -> tuple[int, str, str]:
    done = subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, check=False
    )
    return done.returncode, done.stdout, done.stderr


def parse_worktree_prune(text: str) -> list[str]:
    """Linhas `Removing <registro>: <motivo>` do `worktree prune --dry-run`."""
    prefix = "Removing "
    return [ln[len(prefix) :].strip() for ln in text.splitlines() if ln.startswith(prefix)]


def orphan_worktrees() -> list[str]:
    _, out, err = _git("worktree", "prune", "--dry-run", "--verbose")
    return parse_worktree_prune(out + err)


def parse_remote_prune(text: str) -> list[str]:
    return _WOULD_PRUNE_RE.findall(text)


def stale_remote_refs() -> list[str] | None:
    """Refs `origin/*` sem branch no remoto; `None` se o remoto não respondeu."""
    rc, out, _ = _git("remote", "prune", "--dry-run", "origin")
    return parse_remote_prune(out) if rc == 0 else None


def parse_branch_rows(text: str) -> list[LocalBranch]:
    rows = (ln.split() for ln in text.splitlines() if ln.strip())
    return [LocalBranch(n, sha, int(a), int(b)) for n, sha, a, b in rows]


def local_branches() -> list[LocalBranch] | None:
    """`agent/*` e `claude/*` com ahead/behind contra `origin/main` (git ≥ 2.41)."""
    fmt = "%(refname:short) %(objectname) %(ahead-behind:origin/main)"
    rc, out, _ = _git("for-each-ref", f"--format={fmt}", *BRANCH_NAMESPACES)
    return parse_branch_rows(out) if rc == 0 else None


def checked_out_branches() -> set[str]:
    prefix = "branch refs/heads/"
    _, out, _ = _git("worktree", "list", "--porcelain")
    return {ln[len(prefix) :] for ln in out.splitlines() if ln.startswith(prefix)}


def triage_branches(rows: list[LocalBranch], busy: set[str], classify: Classifier) -> BranchTriage:
    """Entregue = ancestral (ahead 0) ou patch-id em main; o resto fica."""
    free = [r for r in rows if r.name not in busy]
    recent = [r for r in free if r.ahead > 0 and r.behind <= _delivery.TETO_COMMITS]
    alive, by_patch_id, blind = classify([r.name for r in recent]) if recent else ([], [], [])
    delivered_names = set(by_patch_id)
    return BranchTriage(
        delivered=[r for r in free if r.ahead == 0 or r.name in delivered_names],
        checked_out=len(rows) - len(free),
        alive=len(alive),
        beyond_cap=sum(1 for r in free if r.ahead > 0 and r.behind > _delivery.TETO_COMMITS),
        blind_reasons=blind,
    )


def is_major_jump(title: str) -> bool:
    match = _VERSION_JUMP_RE.search(title)
    return bool(match) and match.group(1) != match.group(2)


def _age_days(created_at: str, now: datetime) -> int:
    return (now - datetime.fromisoformat(created_at.replace("Z", "+00:00"))).days


def parse_dependabot(payload: str, now: datetime) -> list[DependabotPr]:
    prs = [
        DependabotPr(
            p["number"], p["title"], _age_days(p["createdAt"], now), is_major_jump(p["title"])
        )
        for p in json.loads(payload)
    ]
    return sorted(prs, key=lambda pr: -pr.age_days)


def dependabot_prs() -> list[DependabotPr] | None:
    """PRs abertos do Dependabot; `None` sem `gh` ou sem rede."""
    if shutil.which("gh") is None:
        return None
    cmd = ["gh", "pr", "list", "--author", "app/dependabot", "--state", "open"]
    cmd += ["--limit", "200", "--json", "number,title,createdAt"]
    done = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    if done.returncode != 0:
        return None
    return parse_dependabot(done.stdout, datetime.now(timezone.utc))


def stash_count() -> int:
    _, out, _ = _git("stash", "list")
    return len(out.splitlines())


@dataclass(frozen=True)
class HygieneState:
    worktrees: list[str]
    remote_refs: list[str] | None
    branches: BranchTriage | None
    stashes: int
    dependabot: list[DependabotPr] | None


def collect_state() -> HygieneState:
    rows = local_branches()
    if rows is not None:
        print(
            f"  · classificando {len(rows)} branches contra origin/main (1–5 min, conforme a carga da máquina)…"
        )
    branches = (
        None
        if rows is None
        else triage_branches(rows, checked_out_branches(), _delivery.classificar)
    )
    return HygieneState(
        worktrees=orphan_worktrees(),
        remote_refs=stale_remote_refs(),
        branches=branches,
        stashes=stash_count(),
        dependabot=dependabot_prs(),
    )


def _line(label: str, value: str) -> None:
    print(f"  {label:.<26} {value}")


def _report_git(state: HygieneState) -> None:
    _line("worktrees órfãos ", f"{len(state.worktrees)}  → git worktree prune")
    for entry in state.worktrees:
        print(f"      · {entry}")
    refs = (
        "remoto não respondeu"
        if state.remote_refs is None
        else f"{len(state.remote_refs)}  → git remote prune origin"
    )
    _line("refs origin/* mortas ", refs)


def _report_branches(triage: BranchTriage | None) -> None:
    if triage is None:
        _line("branches entregues ", "não medido (git ≥ 2.41 e origin/main são necessários)")
        return
    _line(
        "branches entregues ",
        f"{len(triage.delivered)}  → git branch -D (restauração em _scratch/)",
    )
    print(
        f"      · ficam: {triage.checked_out} em checkout num worktree · {triage.alive} vivas · "
        f"{triage.beyond_cap} a mais de {_delivery.TETO_COMMITS} commits de main (não classificadas = vivas)"
    )
    for reason in triage.blind_reasons:
        print(f"      ⚠ sonda cega: {reason}")


def _report_owner_only(state: HygieneState) -> None:
    _line(
        "stash ", f"{state.stashes} entradas — só relato: a pilha é compartilhada entre worktrees"
    )
    if state.dependabot is None:
        _line("PRs do Dependabot ", "não medido (gh ausente ou sem rede)")
        return
    oldest = state.dependabot[0].age_days if state.dependabot else 0
    _line(
        "PRs do Dependabot ",
        f"{len(state.dependabot)} abertos, o mais velho há {oldest}d — só relato: merge é do dono",
    )
    for pr in state.dependabot:
        print(
            f"      · #{pr.number} {pr.age_days:>3}d {'MAJOR' if pr.major else '     '} {pr.title}"
        )


def print_report(state: HygieneState) -> None:
    print("\nHigiene do clone")
    _report_git(state)
    _report_branches(state.branches)
    _report_owner_only(state)


def _write_restore_script(branches: list[LocalBranch]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = REPO_ROOT / "_scratch" / f"hygiene-restore-branches-{stamp}.sh"
    path.parent.mkdir(exist_ok=True)
    lines = [f"git branch {b.name} {b.sha}" for b in branches]
    path.write_text("#!/bin/sh\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def delete_branches(branches: list[LocalBranch]) -> bool:
    """`git branch -D` em lotes; a restauração é gravada ANTES de apagar."""
    if not branches:
        return True
    restore = _write_restore_script(branches)
    ok, deleted = True, 0
    for start in range(0, len(branches), DELETE_CHUNK):
        names = [b.name for b in branches[start : start + DELETE_CHUNK]]
        # o git segue para as demais quando recusa uma (ex.: entrou em checkout desde a triagem)
        rc, out, err = _git("branch", "-D", *names)
        deleted += sum(1 for ln in out.splitlines() if ln.startswith("Deleted branch"))
        ok = ok and rc == 0
        if rc != 0:
            print(f"      ⚠ {err.strip()}")
    print(
        f"      · {deleted} de {len(branches)} apagadas · restaurar: sh {restore.relative_to(REPO_ROOT)}"
    )
    return ok


def _run_step(label: str, *args: str) -> bool:
    rc, _, err = _git(*args)
    print(f"  {'✓' if rc == 0 else '✗'} {label}" + ("" if rc == 0 else f": {err.strip()}"))
    return rc == 0


def apply_fixes(state: HygieneState) -> bool:
    print("\nAplicando")
    results = []
    if state.worktrees:
        results.append(_run_step("git worktree prune", "worktree", "prune", "--verbose"))
    if state.remote_refs:
        results.append(_run_step("git remote prune origin", "remote", "prune", "origin"))
    if state.branches and state.branches.delivered:
        print("  ✓ git branch -D (entregues)")
        results.append(delete_branches(state.branches.delivered))
    if not results:
        print("  · nada a aplicar")
    return all(results)


def _confirmed(assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("\nSem terminal interativo: rode com --yes (make hygiene-fix YES=1).")
        return False
    return input("\nAplicar as remoções acima? (digite 'sim'): ").strip() == "sim"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply", action="store_true", help="remove o que o relatório marca como seguro"
    )
    parser.add_argument("--yes", action="store_true", help="não pergunta antes de aplicar")
    args = parser.parse_args(argv)
    state = collect_state()
    print_report(state)
    if not args.apply:
        print("\n  Nada foi alterado. Para aplicar: make hygiene-fix")
        return 0
    if not _confirmed(args.yes):
        print("  · Abortado, nada foi alterado.")
        return 1
    return 0 if apply_fixes(state) else 1


if __name__ == "__main__":
    sys.exit(main())
