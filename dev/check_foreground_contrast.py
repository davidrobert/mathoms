#!/usr/bin/env python3
"""Gate de contraste do texto contra o fundo NEUTRO (card / muted).

Irmão do `check_tint_contrast.py`, que mede texto sobre tint da própria cor.
Aqui a pergunta é outra e mais simples: **esta cor serve como texto sobre o
fundo liso do relatório?** O ataque de 2026-08-13 (A40.l33) mostrou que a
resposta era "não" em 17 call-sites vivos, todos invisíveis ao gate de tint
porque não havia tint nenhum — o texto estava direto no card.

Duas famílias, as duas medidas e não proibidas por forma:

1. **Token que reprova contra os DOIS fundos neutros.** `--semantic-alert` (e
   seus alias `--semantic-warning`/`--brand-warning`, mesmo hex) dava 2,06:1 em
   light sobre `--surface-card` e 1,88:1 sobre `--surface-muted` — não existe
   fundo neutro da paleta onde esse âmbar sirva de texto. O par `-on-tint` é a
   saída, e vale também no caso-limite de tint 0% (o card liso).
2. **Foreground com opacity modifier.** `text-[var(--X)]/70` compõe o texto com
   o fundo e derruba o contraste — `--surface-muted-foreground` a 70% caía para
   3,55:1 nos dois temas. O gate de tint não modela alpha no foreground.

O conjunto da família 1 é **derivado da paleta**, não escrito à mão: se um token
novo reprovar contra card e muted, entra sozinho. O que precisa de curadoria é o
inverso, e são só duas listas, as duas com o contrato do `NAMED_PAIRS` (entrada
que não corresponde mais ao arquivo falha, em vez de silenciar um call-site
novo): `FUNDO_NAO_NEUTRO`, para texto que não vive sobre fundo neutro e não o
declara na linha; e `LIMIAR_ICONE`, para ícone puro, onde 1.4.11 pede 3:1 e não
4,5. Fundo sólido declarado na própria linha o gate resolve sozinho — texto
branco em botão colorido é correto e mediria 1,00:1 contra o card.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

from check_tint_contrast import (
    AA_TEXTO_PEQUENO,
    SRC,
    TOKENS_CSS,
    canonical,
    composite,
    contrast_ratio,
    token_map,
)

FUNDOS_NEUTROS = ("surface-card", "surface-muted")
# 1.4.11 (objeto gráfico / ícone) — limiar mais baixo que texto, mas existe.
AA_NAO_TEXTO = 3.0

# Call-sites cujo texto NÃO vive sobre fundo neutro E não declara o fundo na
# mesma linha (esse caso o gate resolve sozinho). Cada entrada diz sobre o quê.
FUNDO_NAO_NEUTRO = [
    (
        "components/report/ReportSourceStrip.tsx",
        "surface-border",
        "separadores `·` com aria-hidden — decoração, isenta de 1.4.3/1.4.11",
    ),
]

# Ícone puro sobre fundo neutro: 1.4.11 vale 3:1, não 4,5. Só entra aqui quem
# fica ENTRE os dois limiares — o âmbar reprovava os dois e foi corrigido, que é
# o desfecho certo para "ícone que ninguém enxerga".
LIMIAR_ICONE = [
    (
        "components/report/ReportSectionStub.tsx",
        "brand-neutral",
        "ícone `<Construction/>` do stub de seção — 4,19:1, acima de 1.4.11",
    ),
]

FG_RE = re.compile(r"text-\[var\(--([\w-]+)\)\](?:/(\d+))?")
# Fundo sólido declarado na mesma linha. `bg-[var(--Y)]/N` e `color-mix` ficam
# de fora de propósito: fundo tintado é a classe do `check_tint_contrast.py`.
BG_SOLIDO_RE = re.compile(r"bg-\[var\(--([\w-]+)\)\](?!/)")


class Uso(NamedTuple):
    where: str
    token: str
    alpha: int | None
    fundo: str | None  # fundo sólido declarado na mesma linha, se houver


def _linhas():
    fontes = (p for p in sorted(SRC.rglob("*")) if p.suffix in {".tsx", ".ts"})
    for path in fontes:
        rel = path.relative_to(SRC)
        texto = path.read_text(encoding="utf-8").splitlines()
        yield from ((f"{rel}:{n}", line) for n, line in enumerate(texto, 1))


def _usos_na_linha(where: str, line: str) -> list[Uso]:
    fundo = BG_SOLIDO_RE.search(line)
    return [
        Uso(where, token, int(alpha) if alpha else None, fundo.group(1) if fundo else None)
        for token, alpha in FG_RE.findall(line)
    ]


def _usos() -> list[Uso]:
    return [uso for where, line in _linhas() for uso in _usos_na_linha(where, line)]


def _casa(uso: Uso, entradas) -> str | None:
    for rel, token, motivo in entradas:
        if uso.where.startswith(rel) and uso.token == token:
            return motivo
    return None


def _medida(uso: Uso, fundo: str, theme: str, tokens) -> tuple[float, str, str] | None:
    fg, bg = tokens.get(uso.token), tokens.get(fundo)
    if not (fg and bg):
        return None
    efetivo = composite(fg, bg, uso.alpha) if uso.alpha is not None else fg
    return contrast_ratio(efetivo, bg), f"{fundo}/{theme}", efetivo


def _pior_contra(uso: Uso, themes) -> tuple[float, str, str]:
    """Contraste no pior tema. Fundo declarado na linha manda; senão, os neutros."""
    fundos = (uso.fundo,) if uso.fundo else FUNDOS_NEUTROS
    medidas = (
        _medida(uso, fundo, theme, tokens) for theme, tokens in themes.items() for fundo in fundos
    )
    return min((m for m in medidas if m), default=(99.0, "", ""))


def _sugestao(token: str, alpha: int | None, themes) -> str:
    """`--semantic-warning` é alias de `--semantic-alert`, e o par legível existe
    só sob o nome canônico — sem resolver, a mensagem mandaria usar token que não
    existe, que é o jeito mais barato de um gate perder a confiança de quem lê."""
    if alpha is not None:
        return "remova o modificador de opacidade — ele compõe o texto com o fundo"
    par = f"{canonical(token).removesuffix('-on-tint')}-on-tint"
    if any(par in t for t in themes.values()):
        return f"use --{par}"
    return "esta cor não serve como texto sobre o card; escolha um par legível"


def _falhas(themes) -> tuple[list[str], int]:
    falhas, medidos = [], 0
    for uso in _usos():
        if _casa(uso, FUNDO_NAO_NEUTRO):
            continue
        pior, onde, cor = _pior_contra(uso, themes)
        if pior == 99.0:
            continue
        medidos += 1
        minimo = AA_NAO_TEXTO if _casa(uso, LIMIAR_ICONE) else AA_TEXTO_PEQUENO
        if pior >= minimo:
            continue
        alvo = f"--{uso.token}" + (f"/{uso.alpha}" if uso.alpha else "")
        falhas.append(
            f"{uso.where} — {pior:.2f}:1 em {onde} (text {alvo} → {cor}); "
            f"mínimo {minimo}. {_sugestao(uso.token, uso.alpha, themes)}."
        )
    return falhas, medidos


def _checa_isencoes_stale() -> None:
    nomeadas = [(e, "FUNDO_NAO_NEUTRO") for e in FUNDO_NAO_NEUTRO]
    nomeadas += [(e, "LIMIAR_ICONE") for e in LIMIAR_ICONE]
    for (rel, token, motivo), nome in nomeadas:
        source = (SRC / rel).read_text(encoding="utf-8")
        if f"text-[var(--{token})]" in source:
            continue
        raise SystemExit(
            f"frontend/src/{rel}: isenção stale em {nome} — o arquivo não usa "
            f"mais text-[var(--{token})] ({motivo}). Remova a entrada."
        )


def main() -> int:
    themes = {t: token_map(TOKENS_CSS.read_text(encoding="utf-8"), t) for t in ("light", "dark")}
    _checa_isencoes_stale()
    falhas, medidos = _falhas(themes)
    if not falhas:
        print(
            f"ok — {medidos} uso(s) de cor de texto dentro do limiar "
            f"({len(FUNDO_NAO_NEUTRO)} isento(s) por fundo não neutro, "
            f"{len(LIMIAR_ICONE)} medido(s) a {AA_NAO_TEXTO}:1 por serem ícone)"
        )
        return 0
    print("Texto que reprova contra o fundo neutro do card:\n")
    for falha in falhas:
        print(f"  {falha}")
    print(f"\n{len(falhas)} violação(ões) em {medidos} uso(s) medido(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
