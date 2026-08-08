"""Gate de contraste texto-sobre-tint (dev/check_tint_contrast.py).

Trava: (a) o repo real passa; (b) a aritmética WCAG bate com valores de
referência conhecidos; (c) alias (`warning`↔`alert`) não escapa do pareamento;
(d) o par `-on-tint` não é confundido com "cores diferentes"; (e) um par que
reprova é de fato reportado.

O item (c) é o que o teste existe para proteger: se `is_same_color_pair`
deixasse de resolver alias, `bg: --semantic-warning` + `text: --semantic-warning`
sairia do conjunto medido e o gate ficaria verde por **não olhar**, que é o
modo de falha caro — o teste de (a) sozinho continuaria passando.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ctc", _REPO / "dev" / "check_tint_contrast.py")
assert _spec and _spec.loader
ctc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctc)


def test_repo_real_passa_sob_o_gate() -> None:
    assert ctc.main() == 0


@pytest.mark.parametrize(
    ("fg", "bg", "esperado"),
    [
        ("#FFFFFF", "#000000", 21.0),
        ("#000000", "#FFFFFF", 21.0),
        ("#FFFFFF", "#FFFFFF", 1.0),
    ],
)
def test_contraste_bate_com_referencia(fg: str, bg: str, esperado: float) -> None:
    assert ctc.contrast_ratio(fg, bg) == pytest.approx(esperado, abs=0.01)


def test_composite_em_0_e_100_pct() -> None:
    assert ctc.composite("#FF0000", "#FFFFFF", 100) == "#FF0000"
    assert ctc.composite("#FF0000", "#FFFFFF", 0) == "#FFFFFF"


@pytest.mark.parametrize(
    ("fg", "bg"),
    [
        ("semantic-warning", "semantic-alert"),
        ("semantic-danger", "semantic-loss"),
        ("semantic-success", "semantic-gain"),
        ("semantic-alert-on-tint", "semantic-alert"),
        ("semantic-alert-on-tint", "semantic-warning"),
    ],
)
def test_alias_e_on_tint_continuam_no_conjunto_medido(fg: str, bg: str) -> None:
    """Alias e par corrigido continuam sendo MEDIDOS — sair do conjunto seria
    ficar verde por não olhar."""
    assert ctc.is_same_color_pair(fg, bg)


def test_cores_genuinamente_diferentes_ficam_de_fora() -> None:
    assert not ctc.is_same_color_pair("semantic-gain", "semantic-loss")
    assert not ctc.is_same_color_pair("surface-foreground", "surface-border")


def test_par_que_reprova_e_reportado() -> None:
    """Cor base sobre o próprio tint de 15% — o defeito que criou o gate."""
    pair = ctc.TintPair("fake.tsx:1", "semantic-alert", "semantic-alert", 15)
    tokens = {"semantic-alert": "#F4A261", "surface-card": "#FFFFFF"}
    msg = ctc._violation(pair, "light", tokens)
    assert msg is not None
    assert "1.86:1" in msg
    assert "--semantic-alert-on-tint" in msg


def test_par_corrigido_nao_e_reportado() -> None:
    pair = ctc.TintPair("fake.tsx:1", "semantic-alert-on-tint", "semantic-alert", 15)
    tokens = {
        "semantic-alert": "#F4A261",
        "semantic-alert-on-tint": "#984C11",
        "surface-card": "#FFFFFF",
    }
    assert ctc._violation(pair, "light", tokens) is None


def test_token_sem_hex_falha_em_vez_de_passar_calado() -> None:
    """Token ausente do tema tem de virar falha: silenciar seria fail-open."""
    pair = ctc.TintPair("fake.tsx:1", "inexistente", "semantic-alert", 15)
    msg = ctc._violation(pair, "dark", {"semantic-alert": "#FDBA74", "surface-card": "#1E293B"})
    assert msg is not None
    assert "não consegue medir" in msg
