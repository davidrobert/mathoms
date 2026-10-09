"""Gate de contraste texto-sobre-tint (dev/check_tint_contrast.py).

Trava: (a) o repo real passa; (b) a aritmética WCAG bate com valores de
referência conhecidos; (c) alias (`warning`↔`alert`) não escapa do pareamento;
(d) o par `-on-tint` não é confundido com "cores diferentes"; (e) um par que
reprova é de fato reportado; (f) as quatro sintaxes de tint são pareadas;
(g) o `frontend-ops/` é medido, com a utility nomeada resolvida pelo `@theme`;
(h) a paleta oklch do shadcn/ui é medida, e `dark:` só no tema escuro.

Os itens (c), (f) e (g) são o que o teste existe para proteger, e pelo mesmo
motivo: os modos de ficar verde **por não olhar** — o caro, porque (a) continua
passando. (c) foi hipótese; (f) foi medido — o ataque de 2026-08-13 achou 7
call-sites reprovando (1,86:1 entre eles) que só escreviam o tint como
`bg-[var(--X)]/15` em vez de `bg-[color-mix(…)]`. (g) também foi medido: no
Tailwind v4 do console (#2082) o Badge `success` renderizou a 4,09:1 e nenhum
gate viu, porque nenhum lia o `frontend-ops/` nem a forma `bg-<utility>/N`.
(h) idem: `bg-destructive/10 text-destructive` dos primitivos `button`/`badge`
media 4,01:1 no claro e ficava fora por nome (`fora_da_paleta`), sem hex a medir.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "dev"))
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


_FE = _REPO / "frontend" / "src"
# globals.css do `frontend/` antes do conserto, reduzido ao que o gate lê: o
# `@theme` do shadcn/ui e a paleta oklch de cada tema.
_SHADCN_ANTES = """
@import "../styles/tokens.css";
@custom-variant dark (&:is(.dark *));
@theme inline {
    --color-primary: var(--primary);
    --color-primary-foreground: var(--primary-foreground);
    --color-secondary: var(--secondary);
    --color-secondary-foreground: var(--secondary-foreground);
    --color-destructive: var(--destructive);
}
:root {
    --primary: oklch(0.205 0 0);
    --primary-foreground: oklch(0.985 0 0);
    --secondary: oklch(0.97 0 0);
    --secondary-foreground: oklch(0.205 0 0);
    --destructive: oklch(0.577 0.245 27.325);
}
.dark {
    --primary: oklch(0.922 0 0);
    --primary-foreground: oklch(0.205 0 0);
    --secondary: oklch(0.269 0 0);
    --secondary-foreground: oklch(0.985 0 0);
    --destructive: oklch(0.704 0.191 22.216);
}
"""
# Variante `destructive` do `button.tsx` antes e depois do conserto (ADR-372
# §Emenda 2026-10-09): o tint fica, o texto troca para o par `-on-tint`.
_BUTTON_REVERTIDO = (
    'destructive: "bg-destructive/10 text-destructive hover:bg-destructive/20 '
    'dark:bg-destructive/20 dark:hover:bg-destructive/30",'
)
_BUTTON_CORRIGIDO = (
    'destructive: "bg-destructive/10 text-destructive-on-tint hover:bg-destructive/20 '
    'dark:bg-destructive/20 dark:hover:bg-destructive/30",'
)


def _frontend_em(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, componente: str, globals_css: str | None = None
):
    """Cópia do `frontend/` com o tokens.css REAL, o globals.css real (ou o dado)
    e um componente de uma linha. Fora de `SRC`, então sem os pares nomeados."""
    monkeypatch.setattr(ctc, "ROOT", tmp_path)
    src = tmp_path / "frontend" / "src"
    (src / "styles").mkdir(parents=True)
    (src / "app").mkdir()
    shutil.copy(_FE / "styles/tokens.css", src / "styles/tokens.css")
    css = globals_css or (_FE / "app/globals.css").read_text(encoding="utf-8")
    (src / "app/globals.css").write_text(css, encoding="utf-8")
    (src / "components").mkdir()
    (src / "components" / "ui.tsx").write_text(componente + "\n", encoding="utf-8")
    return ctc.FRONTENDS[0]._replace(
        src=src,
        tokens_css=src / "styles/tokens.css",
        theme_css=(src / "styles/tokens.css", src / "app/globals.css"),
    )


def test_destructive_do_shadcn_e_medido_e_reprova_antes_do_conserto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A paleta oklch do shadcn ficava fora por nome — `bg-destructive/10
    text-destructive` a 4,01:1 no claro passava calado. Cadeia inteira: arquivo →
    `@theme` → `--destructive` oklch → hex → contraste."""
    componente = 'destructive: "bg-destructive/10 text-destructive",'
    _, falhas = ctc.measure_app(_frontend_em(tmp_path, monkeypatch, componente, _SHADCN_ANTES))
    em_claro = [f for f in falhas if "4.01:1 em light" in f]
    assert len(em_claro) == 1, falhas
    assert "frontend/src/components/ui.tsx:1" in em_claro[0]
    assert "text --destructive sobre tint 10% de --destructive" in em_claro[0]


def test_variante_destructive_revertida_reprova_e_a_corrigida_passa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Com o globals.css real: `--destructive` aponta para o vermelho do design
    system, e o texto na cor base ainda reprova o tint de 20% do escuro."""
    _, falhas = ctc.measure_app(_frontend_em(tmp_path, monkeypatch, _BUTTON_REVERTIDO))
    assert any("em dark" in f and "tint 20%" in f for f in falhas), falhas

    pares, falhas = ctc.measure_app(_frontend_em(tmp_path / "b", monkeypatch, _BUTTON_CORRIGIDO))
    assert falhas == []
    assert {(p.fg_token, p.bg_token, p.pct, p.tema) for p in pares} == {
        ("semantic-loss-on-tint", "semantic-danger", 10, None),
        ("semantic-loss-on-tint", "semantic-danger", 20, None),
        ("semantic-loss-on-tint", "semantic-danger", 20, "dark"),
        ("semantic-loss-on-tint", "semantic-danger", 30, "dark"),
    }


def test_variantes_destructive_do_repo_real_sao_medidas() -> None:
    """Não-inércia: os dois primitivos entram no conjunto medido."""
    pares, _ = ctc.measure_app(ctc.FRONTENDS[0])
    medidos = {p.where.split(":")[0] for p in pares if p.bg_token == "semantic-danger"}
    assert {"frontend/src/components/ui/button.tsx", "frontend/src/components/ui/badge.tsx"} <= (
        medidos
    )


def test_tint_com_dark_so_e_medido_no_escuro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`dark:bg-X/30` não pinta pixel no claro. Medi-lo ali reprovava o par
    `-on-tint` cujo valor claro é a base por desenho (ADR-372 D1) — 3,80:1."""
    componente = 'x: "bg-loss/10 text-loss-on-tint dark:hover:bg-loss/30",'
    pares, falhas = ctc.measure_app(_frontend_em(tmp_path, monkeypatch, componente))
    assert falhas == []
    assert {(p.pct, p.tema) for p in pares} == {(10, None), (30, "dark")}


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
    assert ctc._tints_in_line(linha) == [("semantic-gain", 8, "surface-muted", None)]


@pytest.mark.parametrize(
    "linha",
    [
        'className="dark:bg-[color-mix(in_srgb,var(--semantic-gain)_8%,transparent)]"',
        'className="dark:hover:bg-[var(--semantic-gain)]/8"',
        'className="dark:bg-semantic-gain/8"',
    ],
)
def test_prefixo_dark_restringe_o_tint_ao_escuro_nas_tres_formas_de_classe(linha: str) -> None:
    tints = ctc._tints_in_line(linha, {"semantic-gain": "semantic-gain"})
    assert tints == [("semantic-gain", 8, "surface-card", "dark")]


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
        ("text-semantic-gain-on-tint", [("text", "semantic-gain-on-tint", None, False, False)]),
        ("text-surface-muted-fg/60", [("text", "surface-muted-foreground", 60, False, False)]),
        ("hover:bg-semantic-gain/10", [("bg", "semantic-gain", 10, True, False)]),
        ("dark:hover:bg-semantic-gain/30", [("bg", "semantic-gain", 30, True, True)]),
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


@pytest.mark.parametrize(
    ("oklch", "esperado"),
    [
        (("0.577", "0.245", "27.325"), "#E7000B"),  # red-600 publicado pelo Tailwind
        (("57.7%", "0.245", "27.325"), "#E7000B"),
        (("1", "0", "0"), "#FFFFFF"),
        (("0.205", "0", "0"), "#171717"),
    ],
)
def test_oklch_vira_o_hex_que_o_tailwind_publica(oklch: tuple, esperado: str) -> None:
    assert ctc.oklch_hex(*oklch) == esperado


def test_token_map_le_oklch_opaco_e_ignora_translucido() -> None:
    """Cor com alpha não tem hex próprio: fica fora do mapa, e a utility que
    apontar para ela derruba o gate em `utilities` em vez de medir errado."""
    css = ":root { --a: oklch(0.205 0 0); --b: oklch(1 0 0 / 10%); --c: #FFFFFF; }"
    assert ctc.token_map(css, "light") == {"a": "#171717", "c": "#FFFFFF"}


def test_temas_medidos_le_a_paleta_de_todo_css_com_theme(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O `--destructive` vive no globals.css, não no tokens.css — o mapa lia só
    o segundo, e por isso a paleta do shadcn não tinha hex."""
    fe = _frontend_em(tmp_path, monkeypatch, "", _SHADCN_ANTES)
    temas = ctc.temas_medidos(fe)
    assert (temas["light"]["destructive"], temas["dark"]["destructive"]) == ("#E7000B", "#FF6467")
    assert temas["light"]["surface-card"] == "#FFFFFF"


def test_utility_para_cor_translucida_falha(tmp_path: Path) -> None:
    fe = _frontend_com_css(tmp_path, "@theme { --color-border: var(--border); }")
    with pytest.raises(SystemExit, match="border"):
        ctc.utilities(fe, ctc.token_map(":root { --border: oklch(1 0 0 / 10%); }", "light"))


def test_app_so_claro_que_liga_tema_escuro_falha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O console é medido só no claro; a premissa é checada, não só declarada."""
    fe = _ops_em(tmp_path, monkeypatch, 'ok: "bg-semantic-gain/15 dark:bg-surface-card",')
    with pytest.raises(SystemExit, match="tema escuro"):
        ctc.temas_medidos(fe)
