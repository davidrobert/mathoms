#!/usr/bin/env python3
"""Gate de contraste do padrão "texto na cor X sobre tint da MESMA cor X".

O padrão é um tint da cor semântica como fundo junto de `text-[var(--Y)]` no
mesmo `className`: o texto compõe contra um fundo que é a própria cor clareada.
Quando `Y` é `X` (ou um alias dele), o par tende a reprovar WCAG AA — foi assim
que o badge Fator-R chegou a 1,86:1 em light e o selo de risco a 4,36:1 em dark.

Por que MEDIR e não só PROIBIR a forma: a proibição pura reprovaria pares que
passam com folga (tint de 8-10% costuma passar) e, pior, deixaria passar um par
de tokens *diferentes* que contrasta mal. Medir fecha a classe — token novo,
percentual novo ou tema novo entram no cálculo sozinhos, sem editar allowlist.

Medir por UMA sintaxe, porém, não fecha nada: o ataque de 2026-08-13 (A40.l33)
achou 7 call-sites reprovando — inclusive o mesmo 1,86:1 que abriu a lane — só
porque escreviam o tint de outro jeito. As três formas em uso estão em
`_tints_in_line`, e forma nova é o modo de falha a vigiar aqui.

A quarta forma chegou com o Tailwind v4 no `frontend-ops` (#2082): a utility
nomeada `bg-semantic-gain/15`, que o v3 compilava para nada e o v4 renderiza.
Ela reprovou 2 pares no console sem que gate algum visse — o gate não lia o
`frontend-ops/` nem a sintaxe. O nome da utility vira token pelos blocos
`@theme` de cada app (`--color-semantic-gain: var(--semantic-gain)`), então
utility nova entra sozinha.

A paleta oklch do shadcn/ui (`--destructive`… no `globals.css`) ficou fora por
nome até 2026-10-09, sem hex: o `bg-destructive/10 text-destructive` de
`button`/`badge` dava 4,01:1 no claro sem gate que o visse. O mapa de cores lê
`oklch(L C H)` de todo CSS com `@theme`, na ordem do cascade.

Limite honesto: sob tint *translúcido* o fundo é assumido `--surface-card`.
Onde a forma declara o substrato (`color-mix(… , var(--Y))`) o valor é opaco e
o substrato declarado é usado. Componente sobre fundo bem mais escuro/claro que
o card sai medido errado — nesse caso o par tem de ser nomeado em
`NAMED_PAIRS` em vez de inferido.

Segundo limite: o pareamento é dentro de UMA linha. Ícone colorido cujo
`text-[…]` vive num elemento filho não é pareado aqui — entra em `NAMED_PAIRS`.

Terceiro limite: variante (`hover:`, `focus:`) é medida como se fosse
incondicional, nos temas que o app ativa. É o lado conservador — mede a mais,
nunca a menos. A exceção é `dark:`, que não pinta pixel no claro: medi-la ali
reprovava o par `-on-tint` cujo valor claro é a base por desenho (ADR-372 D1).
Tint e texto com `dark:` são medidos só no escuro.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import NamedTuple

from wcag_color import OKLCH_DECL_RE, composite, contrast_ratio, oklch_hex

ROOT = Path(__file__).resolve().parent.parent
TOKENS_CSS = ROOT / "frontend" / "src" / "styles" / "tokens.css"
SRC = ROOT / "frontend" / "src"
OPS_SRC = ROOT / "frontend-ops" / "src"
SEM_UTILITIES: Mapping[str, str] = MappingProxyType({})


class Frontend(NamedTuple):
    """App que consome os tokens: código, hex de cada token, nome de cada utility."""

    src: Path
    tokens_css: Path
    # CSS com `@theme`, na ordem de import: o posterior sobrescreve utility e cor.
    theme_css: tuple[Path, ...]
    temas: tuple[str, ...]


FRONTENDS = (
    Frontend(SRC, TOKENS_CSS, (TOKENS_CSS, SRC / "app" / "globals.css"), ("light", "dark")),
    # Console interno: só o tema claro é ativado. O tokens.css dele traz o bloco
    # dark (mesmo gerador), mas nada no app liga `.dark`/`data-theme` — premissa
    # verificada em `temas_medidos`, não só declarada.
    Frontend(
        OPS_SRC, OPS_SRC / "styles" / "tokens.css", (OPS_SRC / "app" / "globals.css",), ("light",)
    ),
)

AA_TEXTO_PEQUENO = 4.5
# 1.4.11 (objeto gráfico / ícone) — limiar mais baixo que texto, mas existe.
AA_NAO_TEXTO = 3.0


def _par_do_badge_de_alocacao(
    fg: str, tint: str, pct: int
) -> tuple[str, str, str, int, str, float]:
    """Badge do card Atual vs Alvo: tint e texto do mesmo `style`, sobre o card."""
    path = "components/report/cards/alocacaoCardParts.tsx"
    return (path, fg, tint, pct, "surface-card", AA_TEXTO_PEQUENO)


# Pares que o pareamento por linha NÃO alcança: o tint está no elemento pai e o
# `text-[…]` num filho (ícone colorido ao lado de prosa em foreground neutro, ou
# `<p>` logo abaixo do `<div>` tintado). Nomeados à mão porque inferir a relação
# pai↔filho exigiria parsear JSX — e um par nomeado errado é mais fácil de
# auditar que um inferido errado.
#
# `(arquivo, cor do texto, cor do tint, %, substrato, limiar)`. Cada entrada é
# verificada contra o arquivo: se o texto trocar de token OU o tint mudar de
# percentual, a entrada fica stale e o gate falha em vez de medir fantasma.
NAMED_PAIRS = [
    (
        "components/report/provenance/ProvenancePopover.tsx",
        "semantic-alert-on-tint",
        "semantic-alert",
        15,
        "surface-card",
        AA_NAO_TEXTO,
    ),
    (
        "components/report/cards/CascataFiscalCard.pgbl.tsx",
        "semantic-alert-on-tint",
        "semantic-alert",
        10,
        "surface-card",
        AA_NAO_TEXTO,
    ),
    # `alocacaoCardParts.BADGE_COLOR` monta o par por `style` inline, com `bg` e
    # `fg` em linhas separadas de um object literal — o pareamento por linha não
    # alcança. Foi a varredura dark do axe que achou: `rebalancear` dava 4,44:1.
    # Nomeados porque cobrir object literal por regex seria frágil o bastante
    # para virar falso-verde.
    _par_do_badge_de_alocacao("semantic-gain-on-tint", "semantic-success", 12),
    _par_do_badge_de_alocacao("semantic-alert-on-tint", "semantic-warning", 14),
    _par_do_badge_de_alocacao("semantic-loss-on-tint", "semantic-danger", 14),
    _par_do_badge_de_alocacao("surface-muted-foreground-on-tint", "surface-muted-foreground", 15),
    # Pai tintado + `<p>` filho, achados no ataque da A40.l33: a linha do `<div>`
    # não tem `text-[…]` e a linha do `<p>` não tem tint, então nenhuma das duas
    # sozinha vira par. O substrato aqui é declarado (`var(--surface-card)`),
    # logo o tint do `.card-variant-highlight` do card em volta não entra —
    # `color-mix` com segunda cor opaca não compõe com o que está atrás.
    (
        "components/report/cards/EstrategiaAporteCard.tsx",
        "semantic-gain-on-tint",
        "semantic-gain",
        8,
        "surface-card",
        AA_TEXTO_PEQUENO,
    ),
    (
        "components/report/cards/EstrategiaAporteCard.tsx",
        "brand-primary",
        "brand-primary",
        8,
        "surface-card",
        AA_TEXTO_PEQUENO,
    ),
    # S_parecer: tint por `style` inline no `<div>`, texto no `<p>` filho. Passa
    # a 4,76:1 e NÃO foi repintado — a calibragem do S_parecer é do dono
    # (A40.l33 §Deferido). Nomeado para que uma mudança de token não o derrube
    # em silêncio.
    (
        "components/report/sections/SParecer/ParecerHorizonteList.tsx",
        "brand-accent",
        "brand-accent",
        4,
        "surface-card",
        AA_TEXTO_PEQUENO,
    ),
]

# `--semantic-warning` e `--semantic-alert` são o mesmo hex, idem
# danger/loss e success/gain. O par corrigido chama-se `<canônico>-on-tint`,
# então o alias precisa resolver para o canônico antes de comparar — senão
# `bg: warning` + `text: warning` passaria por "tokens diferentes".
ALIAS = {
    "semantic-warning": "semantic-alert",
    "semantic-danger": "semantic-loss",
    "semantic-success": "semantic-gain",
}

# Quatro sintaxes produzem o mesmo pixel; a primeira versão do gate via só a (1).
#   (1) bg-[color-mix(in_srgb,var(--X)_15%,transparent)]  — Tailwind arbitrary
#   (2) color-mix(in srgb, var(--X) 8%, var(--Y))         — substrato declarado,
#       inclusive em `style` inline (espaços em vez de `_`)
#   (3) bg-[var(--X)]/15                                  — opacity modifier
#   (4) bg-semantic-gain/15                               — utility nomeada do
#       `@theme`; o texto pareado vem como `text-semantic-gain`
# (2) é opaca: compõe contra o substrato declarado, não contra o pai.
COLOR_MIX_RE = re.compile(
    r"color-mix\(in[ _]srgb,[ _]*var\(--([\w-]+)\)[ _](\d+)%,[ _]*"
    r"(?:transparent|var\(--([\w-]+)\))\s*\)"
)
OPACITY_BG_RE = re.compile(r"bg-\[var\(--([\w-]+)\)\]/(\d+)")
FG_RE = re.compile(r"text-\[var\(--([\w-]+)\)\]")
NAMED_RE = re.compile(r"(?<![\w-])(bg|text)-([a-z][a-z0-9-]*)(?:/(\d+))?(?![\w/-])")
BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
THEME_BLOCK_RE = re.compile(r"@theme\b[^{;]*\{([^{}]*)\}")
THEME_COLOR_RE = re.compile(r"--color-([\w-]+):\s*var\(--([\w-]+)\)")
TEMA_ESCURO_RE = re.compile(r"(?<![\w-])dark:|data-theme")
DECL_RE = re.compile(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})\b")


def token_map(css: str, theme: str) -> dict[str, str]:
    """Mapa token → hex, com `oklch(L C H)` opaco convertido. `tokens.css` declara
    tema em 4 seletores (`:root`, `[data-report-scope]`, `[data-theme='dark']` e
    `[data-theme='dark'] [data-report-scope]`) e o shadcn em `.dark`, então
    classificar por presença de `dark` no seletor cobre todos."""
    out: dict[str, str] = {}
    for selector, body in BLOCK_RE.findall(css):
        if ("dark" in selector) != (theme == "dark"):
            continue
        out.update(DECL_RE.findall(body))
        out.update((name, oklch_hex(*lch)) for name, *lch in OKLCH_DECL_RE.findall(body))
    return out


def declared_utilities(fe: Frontend) -> dict[str, str]:
    """utility → destino `var(--Y)`, como o Tailwind v4 resolve os `@theme`."""
    out: dict[str, str] = {}
    for path in fe.theme_css:
        css = COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
        for body in THEME_BLOCK_RE.findall(css):
            out.update(THEME_COLOR_RE.findall(body))
    if not out:
        raise SystemExit(
            f"{fe.src}: nenhum `--color-*: var(--…)` em @theme de "
            f"{[p.name for p in fe.theme_css]} — o gate ficaria "
            "cego a `bg-<utility>/N` e `text-<utility>`."
        )
    return out


def utilities(fe: Frontend, tokens: Mapping[str, str]) -> dict[str, str]:
    """utility → token mensurável. Destino sem hex (cor translúcida, `var()`
    encadeado, cor que nenhum CSS do app declara) falha em vez de sair calado."""
    declaradas = declared_utilities(fe)
    if cegas := {u: t for u, t in declaradas.items() if t not in tokens}:
        raise SystemExit(
            f"{fe.src}: utility sem hex opaco nos CSS do app {sorted(cegas.items())} — "
            "o gate ficaria cego a ela."
        )
    return declaradas


def temas_medidos(fe: Frontend) -> dict[str, dict[str, str]]:
    """Mapa token → hex por tema que o app ativa, lido de todo CSS do app na
    ordem do cascade: declaração posterior sobrescreve, como no navegador."""
    if "dark" not in fe.temas:
        _assert_sem_tema_escuro(fe)
    arquivos = dict.fromkeys((fe.tokens_css, *fe.theme_css))
    css = COMMENT_RE.sub("", "\n".join(p.read_text(encoding="utf-8") for p in arquivos))
    return {theme: token_map(css, theme) for theme in fe.temas}


def _assert_sem_tema_escuro(fe: Frontend) -> None:
    for where, line in _source_lines(fe.src):
        if TEMA_ESCURO_RE.search(line):
            raise SystemExit(
                f"{where}: o app é medido só no tema claro, mas "
                "esta linha liga tema escuro — inclua 'dark' em `Frontend.temas`."
            )


class Utility(NamedTuple):
    kind: str  # "bg" | "text"
    token: str
    alpha: int | None
    variante: bool  # prefixada (`hover:`, `dark:`…)
    so_escuro: bool  # `dark:` na cadeia de variantes


def _so_escuro(line: str, inicio: int) -> bool:
    """A classe que contém `line[inicio]` tem `dark:` entre as variantes?"""
    comeco = max(line.rfind(sep, 0, inicio) for sep in " \"'`{") + 1
    return "dark:" in line[comeco:inicio]


def named_utilities(line: str, utilities: Mapping[str, str]) -> list[Utility]:
    """Cada `bg-<u>[/N]` / `text-<u>[/N]` da linha cujo `<u>` é cor do `@theme`."""
    return [
        Utility(
            m[1],
            utilities[m[2]],
            int(m[3]) if m[3] else None,
            line[m.start() - 1 : m.start()] == ":",
            _so_escuro(line, m.start()),
        )
        for m in NAMED_RE.finditer(line)
        if m[2] in utilities
    ]


def canonical(token: str) -> str:
    return ALIAS.get(token, token)


def is_same_color_pair(fg: str, bg: str) -> bool:
    """`text-[var(--X-on-tint)]` sobre tint de `--X` é o par JÁ corrigido —
    continua sendo medido (o valor pode regredir), mas não é "mesma cor"."""
    return canonical(fg).removesuffix("-on-tint") == canonical(bg).removesuffix("-on-tint")


class TintPair(NamedTuple):
    where: str
    fg_token: str
    bg_token: str
    pct: int
    substrate: str = "surface-card"
    min_ratio: float = AA_TEXTO_PEQUENO
    tema: str | None = None  # "dark" quando tint ou texto tem `dark:`


class Tint(NamedTuple):
    token: str
    pct: int
    substrate: str
    tema: str | None


def _tema(line: str, inicio: int) -> str | None:
    return "dark" if _so_escuro(line, inicio) else None


def _tints_in_line(line: str, utilities: Mapping[str, str] = SEM_UTILITIES) -> list[Tint]:
    """Cada tint declarado na linha, com o substrato e o tema em que pinta."""
    mixes = [
        Tint(m[1], int(m[2]), m[3] or "surface-card", _tema(line, m.start()))
        for m in COLOR_MIX_RE.finditer(line)
    ]
    mixes += [
        Tint(m[1], int(m[2]), "surface-card", _tema(line, m.start()))
        for m in OPACITY_BG_RE.finditer(line)
    ]
    return mixes + [
        Tint(u.token, u.alpha, "surface-card", "dark" if u.so_escuro else None)
        for u in named_utilities(line, utilities)
        if u.kind == "bg" and u.alpha is not None
    ]


def _fgs_in_line(
    line: str, utilities: Mapping[str, str] = SEM_UTILITIES
) -> list[tuple[str, str | None]]:
    """`(token, tema)` de cada cor de texto da linha."""
    arbitrarios = [(m[1], _tema(line, m.start())) for m in FG_RE.finditer(line)]
    nomeados = [
        (u.token, "dark" if u.so_escuro else None)
        for u in named_utilities(line, utilities)
        if u.kind == "text"
    ]
    return arbitrarios + nomeados


def _pairs_in_line(
    where: str, line: str, utilities: Mapping[str, str] = SEM_UTILITIES
) -> list[TintPair]:
    fgs = _fgs_in_line(line, utilities)
    return [
        TintPair(where, fg, tint.token, tint.pct, tint.substrate, tema=tint.tema or fg_tema)
        for tint in _tints_in_line(line, utilities)
        for fg, fg_tema in fgs
    ]


# Checar só a cor do texto deixava o percentual apodrecer: o call-site vira 30%
# e o gate segue reportando o contraste de 15%, que ninguém pinta.
def _assert_fresh(
    where: str, source: str, pair: TintPair, utilities: Mapping[str, str] = SEM_UTILITIES
) -> None:
    """Entrada nomeada que não corresponde mais ao arquivo é fantasma."""
    lines = source.splitlines()
    textos = {fg for line in lines for fg, _ in _fgs_in_line(line, utilities)}
    if f"var(--{pair.fg_token})" not in source and pair.fg_token not in textos:
        raise SystemExit(
            f"{where}: entrada stale em NAMED_PAIRS — o arquivo não usa mais "
            f"--{pair.fg_token}. Atualize ou remova a entrada."
        )
    declarados = {(t.token, t.pct) for line in lines for t in _tints_in_line(line, utilities)}
    if (pair.bg_token, pair.pct) not in declarados:
        raise SystemExit(
            f"{where}: entrada stale em NAMED_PAIRS — o arquivo não declara tint "
            f"de --{pair.bg_token} a {pair.pct}%. Atualize o percentual da entrada."
        )


def named_pairs(utilities: Mapping[str, str] = SEM_UTILITIES) -> list[TintPair]:
    """Pares nomeados (texto em elemento filho) + checagem de staleness."""
    out = []
    for rel, fg_token, bg_token, pct, substrate, min_ratio in NAMED_PAIRS:
        pair = TintPair(
            f"frontend/src/{rel} (par nomeado)", fg_token, bg_token, pct, substrate, min_ratio
        )
        _assert_fresh(pair.where, (SRC / rel).read_text(encoding="utf-8"), pair, utilities)
        out.append(pair)
    return out


def _source_lines(src: Path = SRC) -> Iterator[tuple[str, str]]:
    for path in sorted(src.rglob("*")):
        if path.suffix not in {".tsx", ".ts"}:
            continue
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            yield f"{rel}:{lineno}", line


def same_color_pairs(
    src: Path = SRC, utilities: Mapping[str, str] = SEM_UTILITIES
) -> list[TintPair]:
    """Cada linha que declara tint E cor de texto da mesma cor."""
    return [
        pair
        for where, line in _source_lines(src)
        for pair in _pairs_in_line(where, line, utilities)
        if is_same_color_pair(pair.fg_token, pair.bg_token)
    ]


def app_pairs(fe: Frontend, utilities: Mapping[str, str]) -> list[TintPair]:
    """Pares inferidos por linha do app + os nomeados, que são do `frontend/`."""
    pairs = same_color_pairs(fe.src, utilities)
    return pairs + named_pairs(utilities) if fe.src == SRC else pairs


def _violation(pair: TintPair, theme: str, tokens: dict[str, str]) -> str | None:
    fg, bg_base, substrate = (
        tokens.get(pair.fg_token),
        tokens.get(pair.bg_token),
        tokens.get(pair.substrate),
    )
    if not (fg and bg_base and substrate):
        return (
            f"{pair.where} — token sem hex no tema {theme} "
            f"(fg=--{pair.fg_token} bg=--{pair.bg_token} sob --{pair.substrate}); "
            "gate não consegue medir"
        )
    ratio = contrast_ratio(fg, composite(bg_base, substrate, pair.pct))
    if ratio >= pair.min_ratio:
        return None
    return (
        f"{pair.where} — {ratio:.2f}:1 em {theme} "
        f"(text --{pair.fg_token} sobre tint {pair.pct}% de --{pair.bg_token}); "
        f"mínimo {pair.min_ratio}. Use o par --{canonical(pair.bg_token)}-on-tint."
    )


def _report(failures: list[str], measured: int) -> None:
    print("Contraste insuficiente em texto sobre tint da mesma cor:\n")
    for failure in failures:
        print(f"  {failure}")
    print(
        f"\n{len(failures)} violação(ões) em {measured} par(es) medido(s).\n"
        "Corrija trocando a cor do TEXTO pelo par `-on-tint` "
        "(design-tokens/tokens.json), não afrouxando o tint."
    )


def measure_app(fe: Frontend) -> tuple[list[TintPair], list[str]]:
    """Pares medidos do app e as violações deles, em cada tema que ele ativa."""
    themes = temas_medidos(fe)
    pairs = app_pairs(fe, utilities(fe, themes["light"]))
    failures = [
        msg
        for pair in pairs
        for theme, tokens in themes.items()
        if pair.tema in (None, theme) and (msg := _violation(pair, theme, tokens))
    ]
    return pairs, failures


def main() -> int:
    pairs: list[TintPair] = []
    failures: list[str] = []
    for fe in FRONTENDS:
        app_pairs_, app_failures = measure_app(fe)
        pairs, failures = pairs + app_pairs_, failures + app_failures
    if not failures:
        nomeados = sum(1 for p in pairs if p.min_ratio != AA_TEXTO_PEQUENO)
        print(
            f"ok — {len(pairs)} par(es) sobre tint da mesma cor dentro do limiar "
            f"({len(pairs) - nomeados} texto ≥ {AA_TEXTO_PEQUENO}:1, "
            f"{nomeados} não-texto ≥ {AA_NAO_TEXTO}:1)"
        )
        return 0
    _report(failures, len(pairs))
    return 1


if __name__ == "__main__":
    sys.exit(main())
