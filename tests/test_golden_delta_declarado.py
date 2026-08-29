"""O passo de CI que produz o delta de golden — e prova que mediu."""

from __future__ import annotations

import sys
from pathlib import Path

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
