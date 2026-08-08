#!/usr/bin/env python3
"""Gate de contraste do padrão "texto na cor X sobre tint da MESMA cor X".

O padrão é `bg-[color-mix(in_srgb,var(--X)_N%,transparent)]` junto de
`text-[var(--Y)]` no mesmo `className`: o texto compõe contra um fundo que é a
própria cor clareada. Quando `Y` é `X` (ou um alias dele), o par tende a
reprovar WCAG AA — foi assim que o badge Fator-R chegou a 1,86:1 em light e o
selo de risco a 4,36:1 em dark.

Por que MEDIR e não só PROIBIR a forma: a proibição pura reprovaria pares que
passam com folga (tint de 8-10% costuma passar) e, pior, deixaria passar um par
de tokens *diferentes* que contrasta mal. Medir fecha a classe — token novo,
percentual novo ou tema novo entram no cálculo sozinhos, sem editar allowlist.

Limite honesto: o fundo sob o tint transparente é assumido como
`--surface-card`, que é o caso de todos os call-sites de hoje. Um componente
sobre fundo bem mais escuro/claro que o card sai medido errado — se isso
aparecer, o par tem de ser nomeado num teste explícito (padrão de
`parecerToneContrast.test.ts`) em vez de inferido aqui.

Segundo limite: o pareamento é dentro de UM `className`. Ícone colorido cujo
`text-[…]` vive num elemento filho (o `<AlertTriangle>` de `SimplificadaFlag`,
por exemplo) não é pareado aqui — 1.4.11 nesses casos está coberto por teste de
token nomeado, não por este gate.
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

# Pares que o pareamento por `className` NÃO alcança: o tint está no elemento
# pai e o `text-[…]` num filho (ícone colorido ao lado de prosa em foreground
# neutro). Nomeados à mão porque inferir a relação pai↔filho exigiria parsear
# JSX — e um par nomeado errado é mais fácil de auditar que um inferido errado.
# Cada entrada é verificada contra o arquivo: se o call-site sumir ou trocar de
# token, a entrada fica stale e o gate falha em vez de medir fantasma.
NAMED_PAIRS = [
    ("components/report/provenance/ProvenancePopover.tsx", "semantic-alert", 15, AA_NAO_TEXTO),
    ("components/report/cards/CascataFiscalCard.pgbl.tsx", "semantic-alert", 10, AA_NAO_TEXTO),
    # `alocacaoCardParts.BADGE_COLOR` monta o par por `style` inline, com `bg` e
    # `fg` em linhas separadas de um object literal — o pareamento por linha não
    # alcança, e a forma `color-mix(in srgb, …)` (com espaços) nem casa com o
    # arbitrary value do Tailwind. Foi a varredura dark do axe que achou:
    # `rebalancear` dava 4,44:1. Nomeados porque cobrir object literal por regex
    # seria frágil o bastante para virar falso-verde.
    ("components/report/cards/alocacaoCardParts.tsx", "semantic-gain", 12, AA_TEXTO_PEQUENO),
    ("components/report/cards/alocacaoCardParts.tsx", "semantic-alert", 14, AA_TEXTO_PEQUENO),
    ("components/report/cards/alocacaoCardParts.tsx", "semantic-loss", 14, AA_TEXTO_PEQUENO),
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

BG_RE = re.compile(r"bg-\[color-mix\(in_srgb,var\(--([\w-]+)\)_(\d+)%,transparent\)\]")
FG_RE = re.compile(r"text-\[var\(--([\w-]+)\)\]")
BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
DECL_RE = re.compile(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})\b")


def token_map(css: str, theme: str) -> dict[str, str]:
    """Mapa token → hex. `tokens.css` declara tema em 4 seletores distintos
    (`:root`, `:root [data-report-scope]`, `.dark, …`, `.dark [data-report-scope]`),
    então classificar por presença de `dark` no seletor cobre todos."""
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
    min_ratio: float = AA_TEXTO_PEQUENO


def _pair_in_line(where: str, line: str) -> TintPair | None:
    bg = BG_RE.search(line)
    fg = FG_RE.search(line)
    if not (bg and fg):
        return None
    return TintPair(where, fg.group(1), bg.group(1), int(bg.group(2)))


def named_pairs() -> list[TintPair]:
    """Pares nomeados (ícone em elemento filho) + checagem de staleness."""
    out = []
    for rel, bg_token, pct, min_ratio in NAMED_PAIRS:
        fg_token = f"{canonical(bg_token)}-on-tint"
        source = (SRC / rel).read_text(encoding="utf-8")
        where = f"frontend/src/{rel} (par nomeado)"
        if f"var(--{fg_token})" not in source:
            raise SystemExit(
                f"{where}: entrada stale em NAMED_PAIRS — o arquivo não usa mais "
                f"--{fg_token}. Atualize ou remova a entrada."
            )
        out.append(TintPair(where, fg_token, bg_token, pct, min_ratio))
    return out


def _source_lines():
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in {".tsx", ".ts"}:
            continue
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            yield f"{rel}:{lineno}", line


def same_color_pairs() -> list[TintPair]:
    """Cada `className` que declara tint E cor de texto da mesma cor."""
    found = (_pair_in_line(where, line) for where, line in _source_lines())
    return [p for p in found if p and is_same_color_pair(p.fg_token, p.bg_token)]


def _violation(pair: TintPair, theme: str, tokens: dict[str, str]) -> str | None:
    fg, bg_base, card = (
        tokens.get(pair.fg_token),
        tokens.get(pair.bg_token),
        tokens.get("surface-card"),
    )
    if not (fg and bg_base and card):
        return (
            f"{pair.where} — token sem hex no tema {theme} "
            f"(fg=--{pair.fg_token} bg=--{pair.bg_token}); gate não consegue medir"
        )
    ratio = contrast_ratio(fg, composite(bg_base, card, pair.pct))
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
