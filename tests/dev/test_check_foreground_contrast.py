"""Gate de contraste do texto sobre fundo neutro (dev/check_foreground_contrast.py).

Trava: (a) o repo real passa; (b) o fundo declarado na linha manda sobre o
neutro presumido; (c) alpha no foreground entra no cálculo; (d) alias resolve na
mensagem; (e) isenção stale falha em vez de silenciar.

O item (b) é o que separa este gate de uma proibição de token: texto branco
sobre botão sólido é correto e mediria 1,00:1 contra o card. Sem ler o fundo da
própria linha, o gate reprovaria o call-site certo e ensinaria a ignorá-lo.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "dev"))
_spec = importlib.util.spec_from_file_location(
    "cfc", _REPO / "dev" / "check_foreground_contrast.py"
)
assert _spec and _spec.loader
cfc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfc)

TOKENS = {
    "light": {
        "semantic-warning": "#F4A261",
        "semantic-alert-on-tint": "#984C11",
        "surface-card": "#FFFFFF",
        "surface-muted": "#F1F5F9",
        "surface-muted-foreground": "#475569",
        "brand-primary": "#1A3A5C",
        "brand-primary-foreground": "#FFFFFF",
    }
}


def test_repo_real_passa_sob_o_gate() -> None:
    assert cfc.main() == 0


def test_fundo_declarado_na_linha_manda_sobre_o_neutro() -> None:
    """Branco sobre botão sólido é correto; medir contra o card daria 1,00:1."""
    sobre_botao = cfc.Uso("x.tsx:1", "brand-primary-foreground", None, "brand-primary")
    sobre_card = cfc.Uso("x.tsx:1", "brand-primary-foreground", None, None)
    assert cfc._pior_contra(sobre_botao, TOKENS)[0] > 4.5
    assert cfc._pior_contra(sobre_card, TOKENS)[0] == pytest.approx(1.0, abs=0.01)


def test_alpha_no_foreground_entra_no_calculo() -> None:
    cheio = cfc.Uso("x.tsx:1", "surface-muted-foreground", None, "surface-card")
    a_70 = cfc.Uso("x.tsx:1", "surface-muted-foreground", 70, "surface-card")
    assert cfc._pior_contra(cheio, TOKENS)[0] > 4.5
    assert cfc._pior_contra(a_70, TOKENS)[0] < 4.5


def test_pior_tema_e_pior_fundo_ganham() -> None:
    """`--surface-muted` é fundo plausível do mesmo card e mede pior que o card."""
    uso = cfc.Uso("x.tsx:1", "semantic-warning", None, None)
    pior, onde, _ = cfc._pior_contra(uso, TOKENS)
    assert pior == pytest.approx(1.88, abs=0.02)
    assert "surface-muted" in onde


def test_sugestao_resolve_alias() -> None:
    """`--semantic-warning-on-tint` não existe; o par vive sob o nome canônico."""
    assert cfc._sugestao("semantic-warning", None, TOKENS) == "use --semantic-alert-on-tint"


def test_sugestao_de_alpha_aponta_o_modificador() -> None:
    assert "opacidade" in cfc._sugestao("surface-muted-foreground", 70, TOKENS)


def test_isencao_stale_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isenção que sobrevive ao próprio motivo é fail-open."""
    monkeypatch.setattr(
        cfc,
        "FUNDO_NAO_NEUTRO",
        [("components/report/ReportSourceStrip.tsx", "semantic-gain", "motivo inventado")],
    )
    with pytest.raises(SystemExit, match="stale"):
        cfc._checa_isencoes_stale()


def test_bg_tintado_nao_conta_como_fundo_solido() -> None:
    """`bg-[var(--X)]/15` é tint — classe do check_tint_contrast, não desta."""
    assert cfc.BG_SOLIDO_RE.search("bg-[var(--semantic-warning)]/15 text-x") is None
    assert cfc.BG_SOLIDO_RE.search("bg-[var(--brand-primary)] text-x") is not None
