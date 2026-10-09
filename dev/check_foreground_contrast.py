#!/usr/bin/env python3
"""Gate de contraste do texto contra o fundo NEUTRO (card / muted).

Irmão do `check_tint_contrast.py`, que mede texto sobre tint da própria cor.
Aqui a pergunta é outra e mais simples: **esta cor serve como texto sobre o
fundo liso do relatório?** O ataque de 2026-08-13 (A40.l33) mostrou que a
resposta era "não" em 19 call-sites vivos, todos invisíveis ao gate de tint
porque não havia tint nenhum — o texto estava direto no card.

**Duas sintaxes de foreground, e a segunda entrou no MESMO dia em que o gate
nasceu**: escrito só sobre `className`, ele deixou passar 2 call-sites a 1,88:1
em `style={{ color }}` — um deles `role="alert"`, cujo gêmeo em `className` já
estava corrigido no arquivo ao lado. Foi a terceira vez que esta classe reabriu
por sintaxe nesta lane. Antes de declarar classe fechada aqui, procure a forma
que você ainda não enumerou.

Duas famílias de defeito, as duas medidas e não proibidas por forma:

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

**Terceira sintaxe, e a primeira medida nos dois apps**: a utility nomeada do
`@theme` (`text-surface-muted-fg/60`, `text-semantic-alert`). O Tailwind v3 do
`frontend-ops` compilava a forma com `/N` para nada; no v4 (#2082) ela renderiza
e reprovou ali sem que este gate visse — ele não lia o `frontend-ops/` nem a
forma. Resolução utility → token em `check_tint_contrast.utilities`.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

from check_tint_contrast import (
    AA_TEXTO_PEQUENO,
    FRONTENDS,
    ROOT,
    SEM_UTILITIES,
    canonical,
    composite,
    contrast_ratio,
    named_utilities,
    temas_medidos,
    utilities,
)

FUNDOS_NEUTROS = ("surface-card", "surface-muted")
# 1.4.11 (objeto gráfico / ícone) — limiar mais baixo que texto, mas existe.
AA_NAO_TEXTO = 3.0

# Call-sites cujo texto NÃO vive sobre fundo neutro E não declara o fundo na
# mesma linha (esse caso o gate resolve sozinho). Cada entrada diz sobre o quê.
FUNDO_NAO_NEUTRO = [
    (
        "frontend/src/components/report/ReportSourceStrip.tsx",
        "surface-border",
        "separadores `·` com aria-hidden — decoração, isenta de 1.4.3/1.4.11",
    ),
]

# Ícone puro sobre fundo neutro: 1.4.11 vale 3:1, não 4,5. Só entra aqui quem
# fica ENTRE os dois limiares — o âmbar reprovava os dois e foi corrigido, que é
# o desfecho certo para "ícone que ninguém enxerga".
LIMIAR_ICONE = [
    (
        "frontend/src/components/report/ReportSectionStub.tsx",
        "brand-neutral",
        "ícone `<Construction/>` do stub de seção — 4,19:1, acima de 1.4.11",
    ),
]

# Texto cujo fundo vive no componente PAI, fora da linha. Medido contra esse
# fundo em vez de isento: a isenção deixaria de ver regressão do token.
# `(arquivo, token do texto, token do fundo, sobre o quê)`.
FUNDO_NO_PAI = [
    (
        "frontend/src/app/(app)/documents/_components/DocumentRow.tsx",
        "surface-background",
        "surface-foreground",
        "texto do `TooltipContent` do shadcn, que pinta `bg-foreground`",
    ),
] + [
    # `<Spinner>` de carregamento dentro do `<Button>` default, que pinta
    # `bg-primary`. Medidos desde que a paleta oklch do shadcn ganhou hex.
    (rel, "primary-foreground", "primary", "Spinner no `<Button>` default (`bg-primary`)")
    for rel in (
        "frontend/src/app/(app)/documents/_components/PendingReviewQueue.tsx",
        "frontend/src/app/(app)/pipeline/_components/TriggerCard.tsx",
        "frontend/src/app/(app)/pipeline/runs/[runId]/reviews/_components/ReviewActions.tsx",
        "frontend/src/app/login/LoginForm.tsx",
        "frontend/src/app/register/RegisterForm.tsx",
    )
]

FG_RE = re.compile(r"text-\[var\(--([\w-]+)\)\](?:/(\d+))?")
# Fundo sólido declarado na mesma linha. `bg-[var(--Y)]/N` e `color-mix` ficam
# de fora de propósito: fundo tintado é a classe do `check_tint_contrast.py`.
BG_SOLIDO_RE = re.compile(r"bg-\[var\(--([\w-]+)\)\](?!/)")

# Segunda sintaxe de foreground: `style={{ color: "var(--X)" }}`. O gate nasceu
# vendo só a forma `className` e, no mesmo dia, deixou passar 2 call-sites a
# 1,88:1 — um deles `role="alert"`, cujo gêmeo em `className` já estava
# corrigido. É a TERCEIRA vez que a classe reabre por sintaxe nesta lane; a
# lição é que gate que lê código fecha a forma que casou, não a classe.
STYLE_FG_RE = re.compile(r'(?:color|fill|stroke):\s*"var\(--([\w-]+)\)"')
STYLE_BG_RE = re.compile(r'background(?:Color)?:\s*"var\(--([\w-]+)\)"')
# O `style` costuma ser objeto multi-linha, com `background` e `color` em linhas
# irmãs. Janela pequena e declarada: cobre o object literal típico sem virar
# pareamento de arquivo inteiro.
JANELA_STYLE = 6


class Uso(NamedTuple):
    where: str
    token: str
    alpha: int | None
    fundo: str | None  # fundo sólido declarado na mesma linha, se houver


def _arquivos(src):
    fontes = (p for p in sorted(src.rglob("*")) if p.suffix in {".tsx", ".ts"})
    for path in fontes:
        yield path.relative_to(ROOT), path.read_text(encoding="utf-8").splitlines()


def _fundo_solido(line: str, utils: Mapping[str, str]) -> str | None:
    """Fundo sólido incondicional da linha. `hover:bg-X` não é o fundo do texto
    em repouso — medir só contra ele aprovaria o estado que mais se vê."""
    if m := BG_SOLIDO_RE.search(line):
        return m.group(1)
    solidos = (u for u in named_utilities(line, utils) if u.kind == "bg" and u.alpha is None)
    return next((u.token for u in solidos if not u.variante), None)


def _usos_className(where: str, line: str, utils: Mapping[str, str] = SEM_UTILITIES) -> list[Uso]:
    fundo = _fundo_solido(line, utils)
    textos = [(token, int(alpha) if alpha else None) for token, alpha in FG_RE.findall(line)]
    textos += [(u.token, u.alpha) for u in named_utilities(line, utils) if u.kind == "text"]
    return [Uso(where, token, alpha, fundo) for token, alpha in textos]


def _fundo_do_style(linhas: list[str], idx: int) -> str | None:
    """`background` irmão dentro do mesmo object literal de `style`."""
    inicio, fim = max(0, idx - JANELA_STYLE), min(len(linhas), idx + JANELA_STYLE + 1)
    achados = (STYLE_BG_RE.search(linha) for linha in linhas[inicio:fim])
    return next((m.group(1) for m in achados if m), None)


def _usos_style(rel, linhas: list[str], idx: int) -> list[Uso]:
    fundo = _fundo_do_style(linhas, idx)
    return [
        Uso(f"{rel}:{idx + 1}", token, None, fundo) for token in STYLE_FG_RE.findall(linhas[idx])
    ]


def _usos(src, utils: Mapping[str, str]) -> list[Uso]:
    out = []
    for rel, linhas in _arquivos(src):
        for idx, linha in enumerate(linhas):
            out += _usos_className(f"{rel}:{idx + 1}", linha, utils)
            out += _usos_style(rel, linhas, idx)
    return out


def _casa(uso: Uso, entradas) -> tuple[str, ...] | None:
    """Resto da entrada (motivo, ou fundo + motivo) cujo arquivo e token casam."""
    for rel, token, *resto in entradas:
        if uso.where.startswith(f"{rel}:") and uso.token == token:
            return tuple(resto)
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


def _falhas(usos: list[Uso], themes) -> tuple[list[str], int]:
    falhas, medidos = [], 0
    for uso in usos:
        if _casa(uso, FUNDO_NAO_NEUTRO):
            continue
        if no_pai := _casa(uso, FUNDO_NO_PAI):
            uso = uso._replace(fundo=no_pai[0])
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


def _checa_isencoes_stale(usos: list[Uso]) -> None:
    """Entrada cujo arquivo não usa mais o token como texto, em nenhuma sintaxe."""
    nomeadas = [(e, "FUNDO_NAO_NEUTRO") for e in FUNDO_NAO_NEUTRO]
    nomeadas += [(e, "LIMIAR_ICONE") for e in LIMIAR_ICONE]
    nomeadas += [(e, "FUNDO_NO_PAI") for e in FUNDO_NO_PAI]
    vivos = {(uso.where.rsplit(":", 1)[0], uso.token) for uso in usos}
    for (rel, token, *resto), nome in nomeadas:
        if (rel, token) in vivos:
            continue
        raise SystemExit(
            f"{rel}: isenção stale em {nome} — o arquivo não usa mais "
            f"--{token} como cor de texto ({resto[-1]}). Remova a entrada."
        )


def _mede_apps() -> tuple[list[str], int]:
    """Falhas e usos medidos dos dois apps, cada um nos temas que ele ativa."""
    falhas, medidos, usos_todos = [], 0, []
    for fe in FRONTENDS:
        themes = temas_medidos(fe)
        usos = _usos(fe.src, utilities(fe, themes["light"]))
        falhas_app, medidos_app = _falhas(usos, themes)
        falhas, medidos, usos_todos = falhas + falhas_app, medidos + medidos_app, usos_todos + usos
    _checa_isencoes_stale(usos_todos)
    return falhas, medidos


def main() -> int:
    falhas, medidos = _mede_apps()
    if not falhas:
        print(
            f"ok — {medidos} uso(s) de cor de texto dentro do limiar "
            f"({len(FUNDO_NAO_NEUTRO)} isento(s) por fundo não neutro, "
            f"{len(LIMIAR_ICONE)} medido(s) a {AA_NAO_TEXTO}:1 por serem ícone, "
            f"{len(FUNDO_NO_PAI)} contra o fundo do componente pai)"
        )
        return 0
    print("Texto que reprova contra o fundo neutro do card:\n")
    for falha in falhas:
        print(f"  {falha}")
    print(f"\n{len(falhas)} violação(ões) em {medidos} uso(s) medido(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
