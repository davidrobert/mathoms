"""Gate de contraste texto-sobre-tint (dev/check_tint_contrast.py).

Trava: (a) o repo real passa; (b) a aritmética WCAG bate com valores de
referência conhecidos; (c) alias (`warning`↔`alert`) não escapa do pareamento;
(d) o par `-on-tint` não é confundido com "cores diferentes"; (e) um par que
reprova é de fato reportado; (f) as quatro sintaxes de tint são pareadas;
(g) o `frontend-ops/` é medido, com a utility nomeada resolvida pelo `@theme`.

Os itens (c), (f) e (g) são o que o teste existe para proteger, e pelo mesmo
motivo: os modos de ficar verde **por não olhar** — o caro, porque (a) continua
passando. (c) foi hipótese; (f) foi medido — o ataque de 2026-08-13 achou 7
call-sites reprovando (1,86:1 entre eles) que só escreviam o tint como
`bg-[var(--X)]/15` em vez de `bg-[color-mix(…)]`. (g) também foi medido: no
Tailwind v4 do console (#2082) o Badge `success` renderizou a 4,09:1 e nenhum
gate viu, porque nenhum lia o `frontend-ops/` nem a forma `bg-<utility>/N`.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ctc", _REPO / "dev" / "check_tint_contrast.py")
assert _spec and _spec.loader
ctc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctc)


_OPS = _REPO / "frontend-ops" / "src"
# Badge `success` do console antes do conserto do #2082 — mesma linha, cor base.
_BADGE_REVERTIDO = 'success: "bg-semantic-gain/15 text-semantic-gain",'
_BADGE_CORRIGIDO = 'success: "bg-semantic-gain/15 text-semantic-gain-on-tint",'


def _ops_em(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, componente: str):
    """Cópia do frontend-ops com os CSS REAIS e um componente de uma linha."""
    monkeypatch.setattr(ctc, "ROOT", tmp_path)
    src = tmp_path / "frontend-ops" / "src"
    for css in ("app/globals.css", "styles/tokens.css"):
        (src / css).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(_OPS / css, src / css)
    (src / "components").mkdir(exist_ok=True)
    (src / "components" / "ui.tsx").write_text(componente + "\n", encoding="utf-8")
    return ctc.FRONTENDS[1]._replace(
        src=src, tokens_css=src / "styles/tokens.css", theme_css=(src / "app/globals.css",)
    )


def test_repo_real_passa_sob_o_gate() -> None:
    assert ctc.main() == 0


def test_badge_revertido_do_2082_reprova_e_o_corrigido_passa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regressão do #2082: texto na cor base sobre o próprio tint de 15% (≈4,09:1
    no claro). Cadeia inteira — arquivo → `@theme` → token → hex → contraste."""
    _, falhas = ctc.measure_app(_ops_em(tmp_path, monkeypatch, _BADGE_REVERTIDO))
    assert len(falhas) == 1
    assert "frontend-ops/src/components/ui.tsx:1" in falhas[0]
    assert "text --semantic-gain sobre tint 15% de --semantic-gain" in falhas[0]
    assert "--semantic-gain-on-tint" in falhas[0]

    pares, falhas = ctc.measure_app(_ops_em(tmp_path, monkeypatch, _BADGE_CORRIGIDO))
    assert falhas == []
    assert [(p.fg_token, p.bg_token, p.pct) for p in pares] == [
        ("semantic-gain-on-tint", "semantic-gain", 15)
    ]


def test_frontend_ops_e_medido_no_repo_real() -> None:
    """Não-inércia: o app entra no conjunto medido, com o Badge pareado."""
    pares, _ = ctc.measure_app(ctc.FRONTENDS[1])
    assert ("semantic-gain-on-tint", "semantic-gain", 15) in {
        (p.fg_token, p.bg_token, p.pct) for p in pares
    }


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


@pytest.mark.parametrize(
    ("forma", "linha"),
    [
        (
            "arbitrary/transparent",
            'className="bg-[color-mix(in_srgb,var(--semantic-alert)_15%,transparent)]'
            ' text-[var(--semantic-alert)]"',
        ),
        (
            "substrato declarado",
            'className="bg-[color-mix(in_srgb,var(--semantic-alert)_15%,var(--surface-muted))]'
            ' text-[var(--semantic-alert)]"',
        ),
        (
            "opacity modifier",
            'amarelo: "bg-[var(--semantic-alert)]/15 text-[var(--semantic-alert)]",',
        ),
        ("utility nomeada", 'warning: "bg-semantic-alert/15 text-semantic-alert",'),
    ],
)
def test_as_quatro_sintaxes_de_tint_sao_pareadas(forma: str, linha: str) -> None:
    """Sintaxe nova é o modo de falha desta classe: a mesma cor, o mesmo pixel e
    o mesmo defeito, escritos de outro jeito, saíam do conjunto medido."""
    pares = ctc._pairs_in_line("fake.tsx:1", linha, {"semantic-alert": "semantic-alert"})
    assert [(p.fg_token, p.bg_token, p.pct) for p in pares] == [
        ("semantic-alert", "semantic-alert", 15)
    ], forma


def test_substrato_declarado_e_usado_no_lugar_do_card() -> None:
    """`color-mix(…, var(--Y))` é opaco: compõe contra `--Y`, não contra o card
    nem contra o fundo do pai."""
    linha = 'className="bg-[color-mix(in_srgb,var(--semantic-gain)_8%,var(--surface-muted))]"'
    assert ctc._tints_in_line(linha) == [("semantic-gain", 8, "surface-muted")]


def test_pares_nomeados_cobrem_o_que_o_pareamento_por_linha_nao_alcanca() -> None:
    """Duas famílias entram como par nomeado: ícone em elemento filho (1.4.11 =
    3:1) e tint no pai com o texto num filho (texto = 4,5:1)."""
    pares = ctc.named_pairs()
    assert len(pares) == len(ctc.NAMED_PAIRS)
    limiares = {p.min_ratio for p in pares}
    assert limiares == {ctc.AA_NAO_TEXTO, ctc.AA_TEXTO_PEQUENO}


def test_entrada_nomeada_com_texto_stale_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    """Par nomeado cujo call-site trocou de token tem de falhar, não medir
    fantasma — allowlist que sobrevive ao próprio motivo é fail-open."""
    monkeypatch.setattr(
        ctc,
        "NAMED_PAIRS",
        [
            (
                "components/report/provenance/ProvenancePopover.tsx",
                "semantic-gain-on-tint",
                "semantic-alert",
                15,
                "surface-card",
                3.0,
            )
        ],
    )
    with pytest.raises(SystemExit, match="não usa mais"):
        ctc.named_pairs()


def test_entrada_nomeada_com_percentual_stale_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    """Checar só a cor do texto deixava o percentual apodrecer: o call-site vira
    30% e o gate segue reportando o contraste de 15%, que ninguém pinta."""
    monkeypatch.setattr(
        ctc,
        "NAMED_PAIRS",
        [
            (
                "components/report/provenance/ProvenancePopover.tsx",
                "semantic-alert-on-tint",
                "semantic-alert",
                30,
                "surface-card",
                3.0,
            )
        ],
    )
    with pytest.raises(SystemExit, match="não declara tint"):
        ctc.named_pairs()


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


UTILS = {
    "semantic-gain": "semantic-gain",
    "semantic-gain-on-tint": "semantic-gain-on-tint",
    "surface-muted-fg": "surface-muted-foreground",
}


@pytest.mark.parametrize(
    ("linha", "esperado"),
    [
        ("text-semantic-gain-on-tint", [("text", "semantic-gain-on-tint", None, False)]),
        ("text-surface-muted-fg/60", [("text", "surface-muted-foreground", 60, False)]),
        ("hover:bg-semantic-gain/10", [("bg", "semantic-gain", 10, True)]),
        # Nome que não é cor do `@theme` não vira token.
        ("text-sm text-left bg-clip-padding", []),
        # Opacidade arbitrária fica fora — e não pode casar um prefixo do nome.
        ("bg-semantic-gain/[0.15]", []),
        ("context-semantic-gain", []),
    ],
)
def test_utility_nomeada_resolve_nome_inteiro(linha: str, esperado: list) -> None:
    assert [tuple(u) for u in ctc.named_utilities(linha, UTILS)] == esperado


def _frontend_com_css(tmp_path: Path, css: str, **campos) -> object:
    (tmp_path / "globals.css").write_text(css, encoding="utf-8")
    return ctc.FRONTENDS[1]._replace(theme_css=(tmp_path / "globals.css",), **campos)


def test_theme_depois_de_import_e_comentario_e_lido(tmp_path: Path) -> None:
    """O `@import` e o comentário antes do bloco entravam no "seletor" e o bloco
    sumia — a primeira versão leu 0 utilities do console sem reclamar."""
    css = (
        '@import "tailwindcss" source("../");\n/* tokens via @theme { } */\n'
        "@theme inline reference {\n  --font-x: var(--font-x);\n"
        "  --color-semantic-gain: var(--semantic-gain);\n}\n"
    )
    fe = _frontend_com_css(tmp_path, css)
    assert ctc.declared_utilities(fe) == {"semantic-gain": "semantic-gain"}


def test_bloco_theme_posterior_sobrescreve(tmp_path: Path) -> None:
    css = "@theme { --color-x: var(--a); }\n@theme inline { --color-x: var(--b); }"
    assert ctc.declared_utilities(_frontend_com_css(tmp_path, css)) == {"x": "b"}


def test_sem_theme_falha_em_vez_de_medir_zero(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="cego"):
        ctc.declared_utilities(_frontend_com_css(tmp_path, ":root { --x: #fff; }"))


def test_utility_sem_hex_fora_da_lista_falha(tmp_path: Path) -> None:
    """Destino sem hex sairia calado do conjunto medido — fail-open."""
    fe = _frontend_com_css(tmp_path, "@theme { --color-x: var(--inexistente); }")
    with pytest.raises(SystemExit, match="inexistente"):
        ctc.utilities(fe, {"semantic-gain": "#000000"})


def test_fora_da_paleta_isenta_e_entrada_stale_falha(tmp_path: Path) -> None:
    css = "@theme { --color-primary: var(--primary); --color-g: var(--semantic-gain); }"
    fe = _frontend_com_css(tmp_path, css, fora_da_paleta=frozenset({"primary"}))
    assert ctc.utilities(fe, {"semantic-gain": "#000000"}) == {"g": "semantic-gain"}
    stale = fe._replace(fora_da_paleta=frozenset({"primary", "destructive"}))
    with pytest.raises(SystemExit, match="destructive"):
        ctc.utilities(stale, {"semantic-gain": "#000000"})


def test_app_so_claro_que_liga_tema_escuro_falha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O console é medido só no claro; a premissa é checada, não só declarada."""
    fe = _ops_em(tmp_path, monkeypatch, 'ok: "bg-semantic-gain/15 dark:bg-surface-card",')
    with pytest.raises(SystemExit, match="tema escuro"):
        ctc.temas_medidos(fe)
