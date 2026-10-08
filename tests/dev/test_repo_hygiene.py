"""Testes de `dev/repo_hygiene.py` — o que o `make hygiene-fix` pode apagar.

A triagem é a parte que decide remoção, e ela é pura: recebe as branches, o
conjunto em checkout e o classificador. O classificador é injetado como fake
nomeado (CLAUDE.md §Testes), que também registra o que lhe pediram.

A promessa de recuperação é testada sobre um repo git real: apagar e restaurar
pelo script gravado em `_scratch/` devolve cada branch ao mesmo SHA.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dev import repo_hygiene
from dev.repo_hygiene import LocalBranch, triage_branches

TETO = repo_hygiene._delivery.TETO_COMMITS


class RecordingClassifier:
    """Fake de `classificar`: devolve `entregues` declaradas, o resto é vivo."""

    def __init__(self, delivered: set[str], blind: list[str] | None = None) -> None:
        self.delivered = delivered
        self.blind = blind or []
        self.asked: list[str] = []

    def __call__(self, refs: list[str]) -> tuple[list[str], list[str], list[str]]:
        self.asked.extend(refs)
        return (
            [r for r in refs if r not in self.delivered],
            [r for r in refs if r in self.delivered],
            self.blind,
        )


def _branch(name: str, ahead: int, behind: int) -> LocalBranch:
    return LocalBranch(name, f"sha-{name}", ahead, behind)


def _names(triage: repo_hygiene.BranchTriage) -> set[str]:
    return {b.name for b in triage.delivered}


def test_ancestral_de_main_e_entregue_sem_passar_pelo_patch_id() -> None:
    classify = RecordingClassifier(delivered=set())
    triage = triage_branches([_branch("agent/a", 0, TETO + 50)], set(), classify)
    assert _names(triage) == {"agent/a"}
    assert classify.asked == []


def test_branch_em_checkout_nunca_e_entregue_mesmo_ancestral() -> None:
    rows = [_branch("claude/wt", 0, 3), _branch("agent/b", 2, 3)]
    triage = triage_branches(rows, {"claude/wt", "agent/b"}, RecordingClassifier({"agent/b"}))
    assert triage.delivered == []
    assert triage.checked_out == 2


def test_patch_id_decide_so_dentro_do_teto() -> None:
    rows = [
        _branch("agent/squash", 3, 10),
        _branch("agent/viva", 1, 10),
        _branch("agent/velha", 4, TETO + 1),
    ]
    classify = RecordingClassifier(delivered={"agent/squash", "agent/velha"})
    triage = triage_branches(rows, set(), classify)
    assert _names(triage) == {"agent/squash"}
    assert classify.asked == ["agent/squash", "agent/viva"]
    assert (triage.alive, triage.beyond_cap) == (1, 1)


def test_sonda_cega_deixa_branch_viva_e_carrega_o_motivo() -> None:
    classify = RecordingClassifier(
        delivered=set(), blind=["merge-base com origin/main não resolveu"]
    )
    triage = triage_branches([_branch("agent/x", 2, 5)], set(), classify)
    assert triage.delivered == []
    assert triage.blind_reasons == ["merge-base com origin/main não resolveu"]


def test_parse_das_saidas_de_dry_run() -> None:
    prune = "Removing worktrees/wt1654b: gitdir file points to non-existent location\n"
    remote = "Pruning origin\nURL: x\n * [would prune] origin/agent/a/1\n * [would prune] origin/agent/b/2\n"
    assert repo_hygiene.parse_worktree_prune(prune) == [
        "worktrees/wt1654b: gitdir file points to non-existent location"
    ]
    assert repo_hygiene.parse_remote_prune(remote) == ["origin/agent/a/1", "origin/agent/b/2"]


@pytest.mark.parametrize(
    ("title", "major"),
    [
        ("chore(deps)(deps-dev): bump vitest from 3.2.6 to 5.0.3 in /frontend", True),
        ("chore(deps)(deps): bump next from 16.3.0 to 16.4.0 in /frontend", False),
        ("chore(deps)(deps): update pydantic requirement from >=2.0 to >=2.13.5", False),
        ("chore(deps)(deps): bump golang from `4013ae0` to `3680233` in /services/x", False),
        (
            "chore(deps)(deps): bump the patch-and-minor group across 1 directory with 17 updates",
            False,
        ),
    ],
)
def test_salto_de_major_so_com_versao_dos_dois_lados(title: str, major: bool) -> None:
    assert repo_hygiene.is_major_jump(title) is major


def test_dependabot_mais_velho_primeiro() -> None:
    payload = (
        '[{"number": 2, "title": "bump a from 1.0 to 1.1", "createdAt": "2026-10-07T00:00:00Z"},'
        ' {"number": 1, "title": "bump b from 1.0 to 2.0", "createdAt": "2026-09-28T00:00:00Z"}]'
    )
    prs = repo_hygiene.parse_dependabot(payload, datetime(2026, 10, 8, tzinfo=timezone.utc))
    assert [(p.number, p.age_days, p.major) for p in prs] == [(1, 10, True), (2, 1, False)]


def _git(repo: Path, *args: str) -> str:
    cmd = ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args]
    return subprocess.run(cmd, cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "commit", "-q", "--allow-empty", "-m", "init")
    monkeypatch.setattr(repo_hygiene, "REPO_ROOT", root)
    return root


def test_apagar_e_restaurar_devolve_o_mesmo_sha(repo: Path) -> None:
    _git(repo, "checkout", "-q", "-b", "agent/x")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "x")
    _git(repo, "checkout", "-q", "main")
    branches = [LocalBranch("agent/x", _git(repo, "rev-parse", "agent/x"), 1, 0)]
    assert repo_hygiene.delete_branches(branches) is True
    assert _git(repo, "branch", "--list", "agent/x") == ""
    restore = next((repo / "_scratch").glob("hygiene-restore-branches-*.sh"))
    subprocess.run(["sh", str(restore)], cwd=repo, check=True)
    assert _git(repo, "rev-parse", "agent/x") == branches[0].sha


def test_branch_que_entrou_em_checkout_depois_da_triagem_sobrevive(
    repo: Path, tmp_path: Path
) -> None:
    for name in ("agent/livre", "agent/ocupada"):
        _git(repo, "branch", name)
    _git(repo, "worktree", "add", "-q", str(tmp_path / "wt"), "agent/ocupada")
    sha = _git(repo, "rev-parse", "main")
    rows = [LocalBranch("agent/livre", sha, 0, 0), LocalBranch("agent/ocupada", sha, 0, 0)]
    assert repo_hygiene.delete_branches(rows) is False
    assert _git(repo, "branch", "--list", "agent/*", "--format=%(refname:short)") == "agent/ocupada"
