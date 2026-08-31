"""O passo de CI que produz o delta de golden — e prova que mediu."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dev.check_golden_delta_declarado import goldens_tocados  # noqa: E402
from dev.check_golden_rebaseline_isolation import _GOLDEN_PREFIXES  # noqa: E402


# Duas listas de prefixo divergiriam em silêncio, e um golden novo entraria num gate e
# não no outro — o modo de falha que este PR conserta, repetido um nível acima.
def test_o_passo_le_os_prefixos_do_gate_irmao():
    from dev import check_golden_delta_declarado as passo

    assert passo._GOLDEN_PREFIXES is _GOLDEN_PREFIXES


def test_manifesto_nao_e_golden_para_o_diff():
    """Ele viaja com o golden no gate de isolamento, mas não tem delta a medir."""
    tocados = goldens_tocados("HEAD")
    assert all("rebaseline_manifest" not in t for t in tocados)


# `git show <base>:<path>` sobre commit que rebaselinou o view-model. Range real, não
# sintético: o #1807 (`acb3abbb`) é o primeiro PR que tocou este golden depois de ele
# entrar nos prefixos vigiados.
def test_range_real_enxerga_o_view_model():
    import subprocess

    base = subprocess.run(
        ["git", "rev-parse", "acb3abbb~1"], capture_output=True, text=True, cwd=_REPO
    )
    if base.returncode:  # histórico raso (CI shallow sem deepen) — nada a afirmar
        return
    saida = subprocess.run(
        ["git", "diff", "--name-only", f"{base.stdout.strip()}..acb3abbb", "--", *_GOLDEN_PREFIXES],
        capture_output=True,
        text=True,
        cwd=_REPO,
    ).stdout
    assert "backend/tests/snapshots/dogfood_view_model.json" in saida


def test_golden_removido_nao_derruba_o_gate(tmp_path, monkeypatch):
    """Deleção não tem `value_delta` a declarar — o manifesto justifica número que
    MUDOU, e num arquivo removido não há número novo.

    Sem este ramo o gate morria em `FileNotFoundError` ao tentar ler na árvore o
    arquivo que o PR apagou: falha de leitura mascarada de reprovação, e o PR ficava
    vermelho sem dizer o que estava errado. Medido no #1896, que trocou 5 fixtures
    malformadas por 6 corretas.
    """
    import dev.check_golden_delta_declarado as gate

    removido = "tests/fixtures/pipeline_golden/e3/nao-existe-mais-3_reconciled.json"
    assert not (gate.REPO_ROOT / removido).exists()

    monkeypatch.setattr(gate, "goldens_tocados", lambda _base: [removido])
    # `_existe_na_base` não deve nem ser consultado: o ramo do removido vem antes.
    monkeypatch.setattr(
        gate, "_existe_na_base", lambda *_a: pytest.fail("ordem errada: leu a base antes")
    )
    assert gate.main(["--base-sha", "HEAD"]) == 0


def test_o_gate_ainda_mede_golden_que_EXISTE(tmp_path, monkeypatch):
    """Anti-vacuidade do teste acima: se o ramo novo engolisse todo caminho, o gate
    passaria a nunca medir nada e o teste anterior seguiria verde."""
    import dev.check_golden_delta_declarado as gate

    vivo = "backend/tests/snapshots/dogfood_view_model.json"
    assert (gate.REPO_ROOT / vivo).exists()

    medidos: list[str] = []
    monkeypatch.setattr(gate, "goldens_tocados", lambda _base: [vivo])
    monkeypatch.setattr(gate, "_existe_na_base", lambda *_a: True)
    monkeypatch.setattr(gate, "_diff_de", lambda _b, path, _t: medidos.append(path) or 0)
    assert gate.main(["--base-sha", "HEAD"]) == 0
    assert medidos == [vivo], "o gate deixou de medir golden existente"
