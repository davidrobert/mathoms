---
id: A40.l13
type: lane
title: "Copy e design system: primitivo monetário no hero, jargão de implementação, abreviação k/M"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P2
branch_slug: a40-l13-copy-e-design-system
adrs: []
depends_on: ["[[A40.l4]]"]
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p2
  - area/frontend
---

# A40.l13 — `copy-e-design-system` (RV3-23, RV3-24, RV3-25)

> Promovido de P3 para **P2** pelo painel: RV3-23 viola norma **escrita e vigente**
> e atinge um primitivo, não um card.

## Problema

**Primitivo (RV3-23).** Os KPIs do hero não passam pelo primitivo monetário —
`ui/Kpi.tsx:76-86` renderiza string sem `tabular-nums`. **É primitivo, não card**:
afeta todo KPI do relatório, incluindo o hero, que é a primeira coisa que o leitor
vê e onde números desalinhados destroem a comparação. A definição do KPI
protagonista existe só como `title` de `<span>` não-focável — invisível a teclado,
toque e PDF. Viola o §Design System do CLAUDE.md e o checklist de acessibilidade
4.1.2.

**Jargão (RV3-24).** O bloco de premissas fala a língua do código (nome de stage,
endpoint, hash de integridade) — proibido nas diretrizes de copy para a superfície
do produto.

**Abreviação (RV3-25).** `k`/`M` em valor monetário, contra `mil`/`mi`/`bi`. A fonte
é a narrativa E5.N, então o fix definitivo é no gerador; a normalização no render
resolve o sintoma.

## Escopo

- `KpiCard` aceita `ReactNode` no valor; hero passa pelo primitivo monetário.
- Definição sai do `title` para sub-linha ou tooltip focável.
- Reescrever o bloco de premissas em linguagem de produto; datas em pt-BR.
- Normalizar abreviação no render + corrigir o gerador.

## Critério de aceite

- Hook `dev/check_monetary_render.py`: falha se formatação de moeda aparecer em
  componentes de relatório fora do primitivo, citando arquivo:linha.
- Teste de primitivo: KPI renderiza com `font-mono` + `tabular-nums`.
- Definição alcançável por teclado (Tab) e presente no PDF.
- **Verificação renderizada** — spec com fixture `large-values` (exercita
  abreviação e alinhamento) assertando `font-mono`/`tabular-nums` no KPI do hero, e
  ausência de `k`/`M` em valor monetário no `inner_text`. Acessibilidade via
  `frontend/tests/e2e/reports/a11y.@critical.spec.ts` (já existe): a definição do KPI
  tem de ter nome acessível.
