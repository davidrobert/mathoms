"""Testes do gate `dev/check_tracked_symlinks.py`.

Cada caso monta um repo git real e adiciona um symlink real ao índice — a
mutação é a que o truque de worktree faria (symlink das deps apontando para
o clone principal), não uma violação sintética.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dev.check_tracked_symlinks import main as gate_main
from dev.check_tracked_symlinks import violation_reason


def _repo_with_symlink(tmp_path: Path, *, link: str, target: str) -> Path:
    repo = tmp_path / "repo"
    (repo / "frontend-ops").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    link_path = repo / link
    link_path.symlink_to(target)
    # `git add` respeita .gitignore; `--force` reproduz o índice ofensor sem
    # depender do bug de barra final que este PR corrigiu.
    subprocess.run(["git", "-C", str(repo), "add", "--force", link], check=True)
    return repo


def test_alvo_relativo_dentro_do_repo_passa(tmp_path: Path) -> None:
    repo = _repo_with_symlink(tmp_path, link="AGENTS.md", target="CLAUDE.md")
    assert gate_main(["--repo", str(repo)]) == 0


def test_alvo_absoluto_falha(tmp_path: Path) -> None:
    # A mutação de origem: b8460274 rastreou frontend-ops/node_modules com
    # alvo absoluto auto-referencial na máquina do dono. O alvo aqui não imita
    # o homedir real de propósito — literal com `/Users/<nome>` é exatamente o
    # vazamento que o gate anti-PII (ADR-319) barra.
    repo = _repo_with_symlink(
        tmp_path,
        link="frontend-ops/node_modules",
        target="/absoluto/nao-portavel/mathoms.ai/frontend-ops/node_modules",
    )
    assert gate_main(["--repo", str(repo)]) == 1


def test_alvo_relativo_que_escapa_a_raiz_falha(tmp_path: Path) -> None:
    # Mesma não-portabilidade, forma relativa — o gate não pode olhar só o "/".
    repo = _repo_with_symlink(
        tmp_path, link="frontend-ops/node_modules", target="../../deps/node_modules"
    )
    assert gate_main(["--repo", str(repo)]) == 1


def test_repo_sem_symlink_passa(tmp_path: Path) -> None:
    repo = tmp_path / "vazio"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    assert gate_main(["--repo", str(repo)]) == 0


@pytest.mark.parametrize(
    "path,target",
    [
        ("AGENTS.md", "CLAUDE.md"),
        ("frontend-ops/node_modules", "../frontend/node_modules"),
        ("a/b/c.md", "../../docs/c.md"),
    ],
)
def test_alvos_portaveis_nao_sao_violacao(path: str, target: str) -> None:
    assert violation_reason(path, target) is None


@pytest.mark.parametrize(
    "path,target",
    [
        ("frontend-ops/node_modules", "/absoluto/repo/frontend-ops/node_modules"),
        ("deps", "C:\\absoluto\\repo\\deps"),
        ("deps", "C:/absoluto/repo/deps"),
        ("frontend-ops/node_modules", "../../outside"),
        ("top", ".."),
    ],
)
def test_alvos_nao_portaveis_sao_violacao(path: str, target: str) -> None:
    assert violation_reason(path, target) is not None
