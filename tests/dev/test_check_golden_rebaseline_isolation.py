"""O gate de isolamento G-c não pode acusar quem MERGEIA (A40.l98).

Merge commit estagia a união dos dois lados, então ele vê o par golden+produção
que o outro ramo já isolou corretamente no PR dele. O ofensor não é de quem
mergeia e não há commit que se possa separar — daí o modo de CI já pular merge
(``rev-list --no-merges``). Faltava a mesma regra no modo ``--staged``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dev.check_golden_rebaseline_isolation import check_staged, violation

_GOLDEN = "tests/fixtures/pipeline_golden/e3/x-3_reconciled.json"
_PRODUCAO = "pipeline/domain/services/foo.py"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo_com_par_estagiado(tmp_path: Path, *, em_merge: bool) -> Path:
    repo = tmp_path / "r"
    (repo / "tests/fixtures/pipeline_golden/e3").mkdir(parents=True)
    (repo / "pipeline/domain/services").mkdir(parents=True)
    _git(repo.parent, "init", "-q", "r")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / _GOLDEN).write_text("{}")
    (repo / _PRODUCAO).write_text("x = 1\n")
    _git(repo, "add", "-A")
    if em_merge:
        (repo / ".git" / "MERGE_HEAD").write_text("0" * 40 + "\n")
    return repo


@pytest.mark.parametrize("em_merge,espera_erro", [(False, True), (True, False)])
def test_o_gate_acusa_o_par_mas_nao_acusa_quem_mergeia(
    tmp_path, monkeypatch, em_merge, espera_erro
):
    repo = _repo_com_par_estagiado(tmp_path, em_merge=em_merge)
    monkeypatch.chdir(repo)
    assert bool(check_staged()) is espera_erro


def test_o_par_continua_sendo_a_condicao_do_erro():
    """Anti-vacuidade: se `violation` deixasse de acusar o par, o teste acima
    passaria nos DOIS ramos e a mudança pareceria correta."""
    assert violation([_GOLDEN, _PRODUCAO])
    assert not violation([_GOLDEN])
    assert not violation([_PRODUCAO])
