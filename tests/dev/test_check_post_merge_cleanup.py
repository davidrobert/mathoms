"""Testes de `dev/check_post_merge_cleanup.py` — quando o `make stale-check` manda apagar.

O aviso de órfã exige evidência de entrega: PR em estado MERGED, ou upstream
configurado que sumiu do remoto (`[gone]`). Sem upstream é o estado normal de
branch recém-criada e não prova nada.

Entrega prova só o que foi PUBLICADO. Commit feito depois do push/merge existe
apenas no clone, então `git branch -D` só é recomendado quando o tip local está
publicado:

- com PR MERGED, o tip é o `headRefOid` do PR ou está contido nele;
- sem esse head (upstream `[gone]`, ou head fora do clone), a ponta que o remoto
  tinha é irrecuperável depois do prune — publicado é o conteúdo do tip já estar
  em `origin/main` pelo predicado de `dev/_lane_branch_delivery.py` (ancestral ∨
  patch-id do diff agregado, que é o que alcança o squash).

O lado git roda sobre um repo real; o remoto nunca é contatado, então push,
squash-merge e prune são escritos direto nas refs de rastreamento
(`update-ref`/`commit-tree`), que é o estado que `git push -u`, o merge do
GitHub e `git fetch --prune` deixam. O lado `gh` é fake nomeado: injetado em
`_diagnose`, ou como executável no PATH para o `main()` (CLAUDE.md §Testes).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dev import check_post_merge_cleanup as cleanup

BRANCH = "agent/lane-x/20261008-1200"
UNKNOWN_OID = "f" * 40


class FixedPrLookup:
    """Fake de `_pr_state_for_branch`: devolve o PR no estado declarado, ou nenhum."""

    def __init__(self, state: str | None, head: str | None = None) -> None:
        self.state = state
        self.head = head
        self.asked: list[str] = []

    def __call__(self, branch: str) -> dict | None:
        self.asked.append(branch)
        if self.state is None:
            return None
        pr = {"number": 7, "state": self.state, "mergeCommit": None, "url": "u"}
        return pr if self.head is None else {**pr, "headRefOid": self.head}


FAKE_GH = """#!{python}
import json, sys
fields = sys.argv[sys.argv.index("--json") + 1].split(",")
pr = {{"number": 7, "state": "MERGED", "headRefOid": "{head}", "mergeCommit": None, "url": "u"}}
print(json.dumps([{{k: v for k, v in pr.items() if k in fields}}]))
"""


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.dev", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _commit(repo: Path, name: str) -> str:
    (repo / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
    _git(repo, "add", f"{name}.txt")
    _git(repo, "commit", "-q", "-m", name)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    work = tmp_path / "work"
    _git(tmp_path, "init", "-q", "-b", "main", str(work))
    _commit(work, "init")
    _git(work, "remote", "add", "origin", "https://example.invalid/mathoms.git")
    _git(work, "update-ref", "refs/remotes/origin/main", "main")
    _git(work, "checkout", "-q", "-b", BRANCH, "main")
    _commit(work, "trabalho-local")
    monkeypatch.chdir(work)
    monkeypatch.setattr(cleanup._delivery, "REPO_ROOT", work)
    monkeypatch.setattr(cleanup._delivery, "JANELA", {"piso": None, "pids": set()})
    return work


def _tip(repo: Path) -> str:
    return _git(repo, "rev-parse", BRANCH)


def _push_without_upstream(repo: Path) -> None:
    _git(repo, "update-ref", f"refs/remotes/origin/{BRANCH}", BRANCH)


def _publish(repo: Path) -> None:
    _push_without_upstream(repo)
    _git(repo, "branch", "-q", f"--set-upstream-to=origin/{BRANCH}", BRANCH)


def _delete_from_remote(repo: Path) -> None:
    _git(repo, "update-ref", "-d", f"refs/remotes/origin/{BRANCH}")


def _squash_into_main(repo: Path, head: str) -> None:
    tree = _git(repo, "rev-parse", f"{head}^{{tree}}")
    squash = _git(repo, "commit-tree", tree, "-p", "refs/remotes/origin/main", "-m", "squash")
    _git(repo, "update-ref", "refs/remotes/origin/main", squash)


def _path_without_gh(tmp_path: Path) -> str:
    bin_dir = tmp_path / "bin-sem-gh"
    bin_dir.mkdir()
    (bin_dir / "git").symlink_to(shutil.which("git") or "/usr/bin/git")
    return str(bin_dir)


def _path_with_fake_gh(tmp_path: Path, head: str) -> str:
    """Fake do `gh`: como o real, devolve só os campos pedidos em `--json`."""
    bin_dir = Path(_path_without_gh(tmp_path))
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH.format(python=sys.executable, head=head), encoding="utf-8")
    gh.chmod(0o755)
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
def test_pr_mergeado_com_tip_no_head_libera_apagar_qualquer_que_seja_o_upstream(
    repo: Path, upstream: str
) -> None:
    if upstream != "ausente":
        _publish(repo)
    if upstream == "sumiu":
        _delete_from_remote(repo)
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup("MERGED", _tip(repo)))
    assert diagnosis is not None
    assert diagnosis.reason == "PR já mergeada"
    assert diagnosis.pr_info is not None and diagnosis.pr_info["state"] == "MERGED"
    assert diagnosis.unpublished == 0


def test_pr_mergeado_com_tip_contido_no_head_libera_apagar(repo: Path) -> None:
    tree = _git(repo, "rev-parse", f"{BRANCH}^{{tree}}")
    head = _git(repo, "commit-tree", tree, "-p", BRANCH, "-m", "commit só no remoto")
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup("MERGED", head))
    assert diagnosis is not None and diagnosis.unpublished == 0


@pytest.mark.parametrize("extra", [1, 2])
def test_pr_mergeado_com_commits_locais_apos_o_head_conta_os_nao_publicados(
    repo: Path, extra: int
) -> None:
    head = _tip(repo)
    _squash_into_main(repo, head)
    for n in range(extra):
        _commit(repo, f"follow-up-{n}")
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup("MERGED", head))
    assert diagnosis is not None and diagnosis.unpublished == extra


def test_pr_mergeado_com_head_fora_do_clone_e_tip_fora_de_main_nao_prova_nada(
    repo: Path,
) -> None:
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup("MERGED", UNKNOWN_OID))
    assert diagnosis is not None and diagnosis.unpublished is None


@pytest.mark.parametrize("squashed", [True, False])
def test_pr_mergeado_sem_head_cai_no_predicado_de_entrega(repo: Path, squashed: bool) -> None:
    if squashed:
        _squash_into_main(repo, _tip(repo))
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup("MERGED"))
    assert diagnosis is not None
    assert diagnosis.unpublished == (0 if squashed else None)


def test_commits_alem_do_head_que_ja_estao_em_main_liberam_apagar(repo: Path) -> None:
    head = _tip(repo)
    _commit(repo, "follow-up")
    _git(repo, "update-ref", "refs/remotes/origin/main", BRANCH)
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup("MERGED", head))
    assert diagnosis is not None and diagnosis.unpublished == 0


def test_upstream_que_sumiu_sem_conteudo_em_main_nao_prova_publicacao(repo: Path) -> None:
    _publish(repo)
    _delete_from_remote(repo)
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup(None))
    assert diagnosis == cleanup.Diagnosis(
        f"upstream origin/{BRANCH} não existe mais no remoto", None, None
    )


def test_upstream_que_sumiu_com_tip_squashado_em_main_libera_apagar(repo: Path) -> None:
    _publish(repo)
    _squash_into_main(repo, _tip(repo))
    _delete_from_remote(repo)
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup(None))
    assert diagnosis is not None and diagnosis.unpublished == 0


def test_upstream_que_sumiu_com_commit_apos_o_squash_nao_libera_apagar(repo: Path) -> None:
    _publish(repo)
    _squash_into_main(repo, _tip(repo))
    _delete_from_remote(repo)
    _commit(repo, "follow-up")
    diagnosis = cleanup._diagnose(BRANCH, FixedPrLookup(None))
    assert diagnosis is not None and diagnosis.unpublished is None


def test_stale_check_pede_o_head_ao_gh_e_manda_apagar_tip_igual_ao_head(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PATH", _path_with_fake_gh(tmp_path, _tip(repo)))
    assert cleanup.main() == 0
    assert f"git branch -D {BRANCH}" in capsys.readouterr().out


def test_stale_check_com_commit_local_apos_o_merge_nao_manda_apagar(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = _tip(repo)
    _squash_into_main(repo, head)
    _commit(repo, "follow-up")
    monkeypatch.setenv("PATH", _path_with_fake_gh(tmp_path, head))
    assert cleanup.main() == 0
    out = capsys.readouterr().out
    assert "branch -D" not in out
    assert "1 commit(s)" in out
    assert f"git cherry-pick {head[:12]}..{BRANCH}" in out


def test_stale_check_de_upstream_que_sumiu_sem_prova_nao_manda_apagar(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _publish(repo)
    _delete_from_remote(repo)
    monkeypatch.setenv("PATH", _path_without_gh(tmp_path))
    assert cleanup.main() == 0
    out = capsys.readouterr().out
    assert "branch -D" not in out
    assert f"git log --oneline origin/main..{BRANCH}" in out
