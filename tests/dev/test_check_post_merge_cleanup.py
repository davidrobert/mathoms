"""Testes de `dev/check_post_merge_cleanup.py` — quando o `make stale-check` manda apagar.

O aviso recomenda `git branch -D`, então "órfã" exige evidência de entrega: PR
em estado MERGED, ou upstream configurado que sumiu do remoto (`[gone]`). Sem
upstream é o estado normal de branch recém-criada e não prova nada.

O lado git roda sobre um repo real; o remoto nunca é contatado, então publicar
e apagar no remoto são escritos direto na ref de rastreamento (`update-ref`),
que é o estado que `git push -u` e `git fetch --prune` deixam. O lado `gh` é um
fake nomeado injetado em `_diagnose` (CLAUDE.md §Testes).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from dev import check_post_merge_cleanup as cleanup

BRANCH = "agent/lane-x/20261008-1200"


class FixedPrLookup:
    """Fake de `_pr_state_for_branch`: devolve o PR no estado declarado, ou nenhum."""

    def __init__(self, state: str | None) -> None:
        self.state = state
        self.asked: list[str] = []

    def __call__(self, branch: str) -> dict | None:
        self.asked.append(branch)
        if self.state is None:
            return None
        return {"number": 7, "state": self.state, "mergeCommit": None, "url": "u"}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.dev", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    work = tmp_path / "work"
    _git(tmp_path, "init", "-q", "-b", "main", str(work))
    _git(work, "commit", "-q", "--allow-empty", "-m", "init")
    _git(work, "remote", "add", "origin", "https://example.invalid/mathoms.git")
    _git(work, "checkout", "-q", "-b", BRANCH, "main")
    _git(work, "commit", "-q", "--allow-empty", "-m", "trabalho local")
    monkeypatch.chdir(work)
    return work


def _push_without_upstream(repo: Path) -> None:
    _git(repo, "update-ref", f"refs/remotes/origin/{BRANCH}", BRANCH)


def _publish(repo: Path) -> None:
    _push_without_upstream(repo)
    _git(repo, "branch", "-q", f"--set-upstream-to=origin/{BRANCH}", BRANCH)


def _delete_from_remote(repo: Path) -> None:
    _git(repo, "update-ref", "-d", f"refs/remotes/origin/{BRANCH}")


def _path_without_gh(tmp_path: Path) -> str:
    bin_dir = tmp_path / "bin-sem-gh"
    bin_dir.mkdir()
    (bin_dir / "git").symlink_to(shutil.which("git") or "/usr/bin/git")
    return str(bin_dir)


def test_branch_nova_sem_upstream_e_sem_pr_nao_e_orfa(repo: Path) -> None:
    assert cleanup._diagnose(BRANCH, FixedPrLookup(None)) is None


def test_sem_gh_branch_nova_e_silenciosa_no_stale_check(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PATH", _path_without_gh(tmp_path))
    assert cleanup.main() == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("state", ["OPEN", "CLOSED"])
def test_pr_nao_mergeado_sem_upstream_nao_e_orfa(repo: Path, state: str) -> None:
    _push_without_upstream(repo)
    assert cleanup._diagnose(BRANCH, FixedPrLookup(state)) is None


def test_upstream_vivo_com_pr_aberto_nao_e_orfa(repo: Path) -> None:
    _publish(repo)
    assert cleanup._diagnose(BRANCH, FixedPrLookup("OPEN")) is None


@pytest.mark.parametrize("upstream", ["ausente", "vivo", "sumiu"])
def test_pr_mergeado_sinaliza_qualquer_que_seja_o_upstream(repo: Path, upstream: str) -> None:
    if upstream != "ausente":
        _publish(repo)
    if upstream == "sumiu":
        _delete_from_remote(repo)
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup("MERGED"))
    assert diagnosis is not None
    assert diagnosis[0] == "PR já mergeada"
    assert diagnosis[1] is not None and diagnosis[1]["state"] == "MERGED"


def test_upstream_que_sumiu_do_remoto_sinaliza_mesmo_sem_gh(repo: Path) -> None:
    _publish(repo)
    _delete_from_remote(repo)
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup(None))
    assert diagnosis == (f"upstream origin/{BRANCH} não existe mais no remoto", None)
