"""Gate de contraste do texto sobre fundo neutro (dev/check_foreground_contrast.py).

Trava: (a) o repo real passa; (b) o fundo declarado na linha manda sobre o
neutro presumido; (c) alpha no foreground entra no cálculo; (d) alias resolve na
mensagem; (e) isenção stale falha em vez de silenciar; (f) a utility nomeada do
`@theme` (`text-surface-muted-fg/60`) é medida, no `frontend/` e no
`frontend-ops/` — no console ela reprovou a 2,77:1 sem gate que visse (#2082).

O item (b) é o que separa este gate de uma proibição de token: texto branco
sobre botão sólido é correto e mediria 1,00:1 contra o card. Sem ler o fundo da
própria linha, o gate reprovaria o call-site certo e ensinaria a ignorá-lo.
"""

from __future__ import annotations

import importlib.util
import shutil
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
    rel = "frontend/src/components/report/ReportSourceStrip.tsx"
    vivo = cfc.Uso(f"{rel}:12", "surface-border", None, None)
    monkeypatch.setattr(cfc, "LIMIAR_ICONE", [])
    monkeypatch.setattr(cfc, "FUNDO_NO_PAI", [])
    monkeypatch.setattr(cfc, "FUNDO_NAO_NEUTRO", [(rel, "semantic-gain", "motivo inventado")])
    with pytest.raises(SystemExit, match="stale"):
        cfc._checa_isencoes_stale([vivo])
    monkeypatch.setattr(cfc, "FUNDO_NAO_NEUTRO", [(rel, "surface-border", "separador")])
    cfc._checa_isencoes_stale([vivo])


def test_bg_tintado_nao_conta_como_fundo_solido() -> None:
    """`bg-[var(--X)]/15` é tint — classe do check_tint_contrast, não desta."""
    assert cfc.BG_SOLIDO_RE.search("bg-[var(--semantic-warning)]/15 text-x") is None
    assert cfc.BG_SOLIDO_RE.search("bg-[var(--brand-primary)] text-x") is not None


def test_foreground_por_style_inline_e_pareado() -> None:
    """A 3ª vez que esta classe reabriu foi por sintaxe: o gate nasceu vendo só
    `className` e deixou passar `style={{color}}` a 1,88:1 no mesmo dia."""
    linhas = ['<span role="alert" style={{ gap: 4, color: "var(--semantic-warning)" }}>']
    usos = cfc._usos_style("x.tsx", linhas, 0)
    assert [(u.token, u.alpha, u.fundo) for u in usos] == [("semantic-warning", None, None)]


def test_style_usa_o_background_irmao_do_mesmo_objeto() -> None:
    """`background` e `color` vivem em linhas irmãs do object literal; sem olhar
    a vizinhança, texto branco em botão sólido mediria 1,00:1 e reprovaria."""
    linhas = [
        "const BTN_ACTIVE_STYLE: CSSProperties = {",
        '  background: "var(--brand-primary)",',
        '  color: "var(--surface-card)",',
        "};",
    ]
    (uso,) = cfc._usos_style("x.tsx", linhas, 2)
    assert uso.fundo == "brand-primary"
    assert cfc._pior_contra(uso, TOKENS)[0] > 4.5


def test_style_sem_background_cai_nos_neutros() -> None:
    linhas = ['  <Badge style={{ color: "var(--semantic-warning)" }}>']
    (uso,) = cfc._usos_style("x.tsx", linhas, 0)
    assert uso.fundo is None
    assert cfc._pior_contra(uso, TOKENS)[0] < 4.5


UTILS = {
    "surface-muted-fg": "surface-muted-foreground",
    "brand-primary": "brand-primary",
    "brand-primary-fg": "brand-primary-foreground",
}


def test_utility_nomeada_com_alpha_e_medida() -> None:
    """A forma que o Tailwind v3 do console compilava para nada e o v4 renderiza."""
    (uso,) = cfc._usos_className(
        "x.tsx:1", '<span className="italic text-surface-muted-fg/60">', UTILS
    )
    assert (uso.token, uso.alpha, uso.fundo) == ("surface-muted-foreground", 60, None)
    assert cfc._pior_contra(uso, TOKENS)[0] < 4.5


def test_bg_nomeado_solido_e_fundo_e_variante_nao_e() -> None:
    """`hover:bg-X` não é o fundo do texto em repouso: medir só contra ele
    aprovaria o estado que mais se vê."""
    (botao,) = cfc._usos_className("x.tsx:1", "bg-brand-primary text-brand-primary-fg", UTILS)
    assert botao.fundo == "brand-primary"
    (hover,) = cfc._usos_className("x.tsx:1", "hover:bg-brand-primary text-brand-primary-fg", UTILS)
    assert hover.fundo is None


def test_fundo_no_pai_mede_contra_o_fundo_declarado() -> None:
    """Texto claro de tooltip escuro: isento seria cego; contra o card, 1,00:1."""
    rel = cfc.FUNDO_NO_PAI[0][0]
    uso = cfc.Uso(f"{rel}:1", "surface-background", 80, None)
    tokens = {
        "light": {
            "surface-background": "#F8FAFC",
            "surface-foreground": "#0F172A",
            "surface-card": "#FFFFFF",
            "surface-muted": "#F1F5F9",
        }
    }
    assert cfc._falhas([uso], tokens) == ([], 1)
    assert cfc._falhas([uso._replace(where="outro.tsx:1")], tokens)[0]


def _ops_em(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Cópia do frontend-ops com os CSS REAIS dele, fora do repo."""
    src = tmp_path / "frontend-ops" / "src"
    for css in ("app/globals.css", "styles/tokens.css"):
        (src / css).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(_REPO / "frontend-ops" / "src" / css, src / css)
    monkeypatch.setattr(cfc, "ROOT", tmp_path)
    monkeypatch.setattr(sys.modules["check_tint_contrast"], "ROOT", tmp_path)
    return cfc.FRONTENDS[1]._replace(
        src=src, tokens_css=src / "styles/tokens.css", theme_css=(src / "app/globals.css",)
    )


def _falhas_do_ops(fe, classe: str) -> list[str]:
    (fe.src / "page.tsx").write_text(f'<span className="italic {classe}">—</span>\n')
    themes = cfc.temas_medidos(fe)
    return cfc._falhas(cfc._usos(fe.src, cfc.utilities(fe, themes["light"])), themes)[0]


def test_muted_fg_60_revertido_do_2082_reprova_no_ops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regressão do #2082 no console: o `/60` reprova (≈2,77:1 sobre muted) e a
    forma sem modificador passa."""
    fe = _ops_em(tmp_path, monkeypatch)
    (falha,) = _falhas_do_ops(fe, "text-surface-muted-fg/60")
    assert "frontend-ops/src/page.tsx:1" in falha
    assert "--surface-muted-foreground/60" in falha
    assert _falhas_do_ops(fe, "text-surface-muted-fg") == []
