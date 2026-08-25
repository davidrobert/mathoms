"""Gate de citação órfã: mover/deletar código não deixa ADR apontando p/ vazio.

Cada caso monta um repo git sintético e roda o gate de verdade — o alvo é o
comportamento fim-a-fim, não a assinatura das funções.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parent.parent / "dev" / "check_doc_code_paths.py"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repo com um módulo de código e uma ADR que o cita."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")

    (tmp_path / "backend" / "app" / "services").mkdir(parents=True)
    (tmp_path / "backend/app/services/vault.py").write_text("x = 1\n")
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs/adr/001-x.md").write_text(
        "O cofre vive em `backend/app/services/vault.py` hoje.\n"
    )
    (tmp_path / "dev").mkdir()
    (tmp_path / "dev" / GATE.name).write_bytes(GATE.read_bytes())
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "seed")
    return tmp_path


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo / "dev" / GATE.name)],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_delecao_com_citacao_viva_reprova(repo: Path) -> None:
    _git(repo, "rm", "-q", "backend/app/services/vault.py")
    result = _run(repo)
    assert result.returncode == 1, result.stdout
    assert "docs/adr/001-x.md" in result.stdout
    assert "deletado" in result.stdout


def test_rename_nomeia_o_destino(repo: Path) -> None:
    (repo / "backend/app/services/security").mkdir()
    _git(repo, "mv", "backend/app/services/vault.py", "backend/app/services/security/vault.py")
    result = _run(repo)
    assert result.returncode == 1, result.stdout
    # o destino entra na mensagem: é o que o autor precisa para consertar a citação
    assert "security/vault.py" in result.stdout


def test_delecao_sem_citacao_passa(repo: Path) -> None:
    (repo / "backend/app/services/outro.py").write_text("y = 2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "outro")
    _git(repo, "rm", "-q", "backend/app/services/outro.py")
    assert _run(repo).returncode == 0


def test_citacao_so_em_lane_nao_gateia(repo: Path) -> None:
    """`docs/sprint` cita arquivo que a própria lane vai criar — fora de escopo."""
    (repo / "docs" / "sprint").mkdir()
    (repo / "docs/sprint/l1.md").write_text("entrega `backend/app/services/vault.py`\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "lane")
    _git(repo, "rm", "-q", "docs/adr/001-x.md")
    _git(repo, "commit", "-qm", "tira a adr")
    _git(repo, "rm", "-q", "backend/app/services/vault.py")
    assert _run(repo).returncode == 0


def test_arquivo_nao_codigo_nao_dispara(repo: Path) -> None:
    """README deletado não é citação de código — o gate não é um link-checker."""
    (repo / "backend" / "LEIAME.md").write_text("nada\n")
    (repo / "docs/adr/002-y.md").write_text("vive em `backend/LEIAME.md`\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "md")
    _git(repo, "rm", "-q", "backend/LEIAME.md")
    assert _run(repo).returncode == 0


def test_gate_do_repo_real_esta_verde() -> None:
    """Sem código staged, o gate não pode reprovar o próprio repo."""
    result = subprocess.run(
        [sys.executable, str(GATE)], cwd=GATE.parent.parent, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout
