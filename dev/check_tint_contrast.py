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

Limite honesto: sob tint *translúcido* o fundo é assumido `--surface-card`.
Onde a forma declara o substrato (`color-mix(… , var(--Y))`) o valor é opaco e
o substrato declarado é usado. Componente sobre fundo bem mais escuro/claro que
o card sai medido errado — nesse caso o par tem de ser nomeado em
`NAMED_PAIRS` em vez de inferido.

Segundo limite: o pareamento é dentro de UMA linha. Ícone colorido cujo
`text-[…]` vive num elemento filho não é pareado aqui — entra em `NAMED_PAIRS`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
TOKENS_CSS = ROOT / "frontend" / "src" / "styles" / "tokens.css"
SRC = ROOT / "frontend" / "src"

AA_TEXTO_PEQUENO = 4.5
# 1.4.11 (objeto gráfico / ícone) — limiar mais baixo que texto, mas existe.
AA_NAO_TEXTO = 3.0

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
    (
        "components/report/cards/alocacaoCardParts.tsx",
        "semantic-gain-on-tint",
        "semantic-success",
        12,
        "surface-card",
        AA_TEXTO_PEQUENO,
    ),
    (
        "components/report/cards/alocacaoCardParts.tsx",
        "semantic-alert-on-tint",
        "semantic-warning",
        14,
        "surface-card",
        AA_TEXTO_PEQUENO,
    ),
    (
        "components/report/cards/alocacaoCardParts.tsx",
        "semantic-loss-on-tint",
        "semantic-danger",
        14,
        "surface-card",
        AA_TEXTO_PEQUENO,
    ),
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

# Três sintaxes produzem o mesmo pixel; a primeira versão do gate via só a (1).
#   (1) bg-[color-mix(in_srgb,var(--X)_15%,transparent)]  — Tailwind arbitrary
#   (2) color-mix(in srgb, var(--X) 8%, var(--Y))         — substrato declarado,
#       inclusive em `style` inline (espaços em vez de `_`)
#   (3) bg-[var(--X)]/15                                  — opacity modifier
# (2) é opaca: compõe contra o substrato declarado, não contra o pai.
COLOR_MIX_RE = re.compile(
    r"color-mix\(in[ _]srgb,[ _]*var\(--([\w-]+)\)[ _](\d+)%,[ _]*"
    r"(?:transparent|var\(--([\w-]+)\))\s*\)"
)
OPACITY_BG_RE = re.compile(r"bg-\[var\(--([\w-]+)\)\]/(\d+)")
FG_RE = re.compile(r"text-\[var\(--([\w-]+)\)\]")
BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
DECL_RE = re.compile(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})\b")


def token_map(css: str, theme: str) -> dict[str, str]:
    """Mapa token → hex. `tokens.css` declara tema em 4 seletores distintos
    (`:root`, `[data-report-scope]`, `[data-theme='dark']` e
    `[data-theme='dark'] [data-report-scope]`), então classificar por presença
    de `dark` no seletor cobre todos."""
    out: dict[str, str] = {}
    for selector, body in BLOCK_RE.findall(css):
        if ("dark" in selector) != (theme == "dark"):
            continue
        for name, hex_value in DECL_RE.findall(body):
            out[name] = hex_value
    return out


def channels(hex_value: str) -> tuple[int, int, int]:
    h = hex_value.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def relative_luminance(hex_value: str) -> float:
    def lin(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = channels(hex_value)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = relative_luminance(fg), relative_luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def composite(color: str, over: str, pct: int) -> str:
    f, b = channels(color), channels(over)
    a = pct / 100
    return "#" + "".join(f"{round(v * a + b[i] * (1 - a)):02X}" for i, v in enumerate(f))


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


def _tints_in_line(line: str) -> list[tuple[str, int, str]]:
    """`(token, %, substrato)` de cada tint declarado na linha."""
    mixes = [
        (token, int(pct), substrate or "surface-card")
        for token, pct, substrate in COLOR_MIX_RE.findall(line)
    ]
    return mixes + [(token, int(pct), "surface-card") for token, pct in OPACITY_BG_RE.findall(line)]


def _pairs_in_line(where: str, line: str) -> list[TintPair]:
    fgs = FG_RE.findall(line)
    return [
        TintPair(where, fg, bg, pct, substrate)
        for bg, pct, substrate in _tints_in_line(line)
        for fg in fgs
    ]


# Checar só a cor do texto deixava o percentual apodrecer: o call-site vira 30%
# e o gate segue reportando o contraste de 15%, que ninguém pinta.
def _assert_fresh(where: str, source: str, pair: TintPair) -> None:
    """Entrada nomeada que não corresponde mais ao arquivo é fantasma."""
    if f"var(--{pair.fg_token})" not in source:
        raise SystemExit(
            f"{where}: entrada stale em NAMED_PAIRS — o arquivo não usa mais "
            f"--{pair.fg_token}. Atualize ou remova a entrada."
        )
    declarados = {(t, p) for line in source.splitlines() for t, p, _ in _tints_in_line(line)}
    if (pair.bg_token, pair.pct) not in declarados:
        raise SystemExit(
            f"{where}: entrada stale em NAMED_PAIRS — o arquivo não declara tint "
            f"de --{pair.bg_token} a {pair.pct}%. Atualize o percentual da entrada."
        )


def named_pairs() -> list[TintPair]:
    """Pares nomeados (texto em elemento filho) + checagem de staleness."""
    out = []
    for rel, fg_token, bg_token, pct, substrate, min_ratio in NAMED_PAIRS:
        pair = TintPair(
            f"frontend/src/{rel} (par nomeado)", fg_token, bg_token, pct, substrate, min_ratio
        )
        _assert_fresh(pair.where, (SRC / rel).read_text(encoding="utf-8"), pair)
        out.append(pair)
    return out


def _source_lines():
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in {".tsx", ".ts"}:
            continue
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            yield f"{rel}:{lineno}", line


def same_color_pairs() -> list[TintPair]:
    """Cada linha que declara tint E cor de texto da mesma cor."""
    return [
        pair
        for where, line in _source_lines()
        for pair in _pairs_in_line(where, line)
        if is_same_color_pair(pair.fg_token, pair.bg_token)
    ]


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


def main() -> int:
    css = TOKENS_CSS.read_text(encoding="utf-8")
    themes = {t: token_map(css, t) for t in ("light", "dark")}
    pairs = same_color_pairs() + named_pairs()
    failures = [
        msg
        for pair in pairs
        for theme, tokens in themes.items()
        if (msg := _violation(pair, theme, tokens))
    ]
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
