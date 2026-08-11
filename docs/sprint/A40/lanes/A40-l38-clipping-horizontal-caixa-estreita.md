---
id: A40.l38
type: lane
title: "Clipping horizontal em caixa ≤700px: o dado sai do relatório sem deixar rastro"
sprint: A40
status: in_progress
priority: P1
branch_slug: a40-l38-clipping-horizontal-caixa-estreita
adrs:
  - "[[ADR-376]]"
  - "[[ADR-076]]"
  - "[[ADR-129]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/frontend
  - area/design-system
  - area/report
---

# A40.l38 — `clipping-horizontal-caixa-estreita`

## Problema

Em caixa estreita o relatório **perdia dado sem deixar rastro**. Não é questão
estética: `document.scrollWidth == innerWidth` em 390px, ou seja a página não
rola horizontalmente — o que passa da borda direita do `<article>` fica
inalcançável, não "cortado".

Medido em 2026-08-11 por sonda derivada do DOM (todo nó cuja borda direita passa
a do `<article>`, descontado o que esteja dentro de contêiner rolável), sobre 3
fixtures × 3 superfícies:

| sintoma | superfície | fora da caixa |
| --- | --- | --- |
| coluna Δ da tabela Antes/Depois (V0) | 390px | **301px** |
| resumo editorial de seção (S3, S4) | 390px | 263px |
| hero "+R$ 41.918,51" (V0) | 390px | 53px |
| badge de regime + Fator-R (S8) | 390px | 145px |
| tabela de imóveis, 5 colunas (S4) | 390px | 108px |
| seletor de período (S2) | 390px | 56px |

O **papel** é o segundo regime, e o mais perigoso porque não tinha sintoma: a
tabela do V0 exigia 691px de caixa e a A4 útil tem 703px. Doze pixels de folga,
sem gate. Qualquer rótulo mais longo ou um dígito a mais no valor tirava a coluna
do julgamento do arquivo que o cliente manda ao contador.

Duas premissas do brief original foram **refutadas por medição** e mudaram o
escopo:

1. *"O `px-10` do `<article>` come 80px do PDF"* — falso. `report-print.css` zera
   o padding em `[data-report-mode]`; no papel a caixa útil é 703px inteiros
   (medido: `articlePadding: "0px / 0px"`). O gutter só machuca o telefone.
2. *"A tabela do V0 corta a coluna Δ no PDF"* — não reproduz. Com dados de 8
   dígitos, o PDF real (gerado pela mesma chamada CDP do `pdf_renderer.py`)
   renderiza as 4 colunas e as setas ▲ com folga. O sintoma relatado é da
   **fronteira**: aparece a partir de ~691px, e uma captura de viewport estreito
   (media `screen`, onde o `px-10` continua valendo) o reproduz. O defeito é
   real; a superfície nomeada no brief é que estava trocada.

## Escopo

Entregue no commit `37ba3af4`. Cada mudança tem causa própria — não é um
`min-w-0` espalhado:

- **`ReportSection`** — `grid-cols-1` explícito + `[&>*]:min-w-0`. O track era
  `auto` e crescia até o `max-content` do filho mais largo, arrastando os
  irmãos; como vale abaixo de 768px, atingia o PDF inteiro ([[ADR-376]] D5).
- **`VariacaoSection` (V0)** — tabela vira lista rótulo/valor abaixo de `sm:`
  (640px, não 768px: a caixa A4 receberia a pilha sem precisar), com cor, glifo
  e `aria-label` preservados juntos ([[ADR-376]] D4). O rótulo passa a quebrar e
  os valores não: o `min-content` da tabela no papel cai de **417px para 308px**,
  e a folga de 12px vira ~347px. Sai o `break-inside: avoid` inline, que
  contrariava a política escrita em `report-print.css`.
- **`ReportCard`** — header com `flex-wrap`; `shrink-0` passa a `min-w-0
  sm:shrink-0`. O `shrink-0` fixava o `headerRight` no `max-content` e **anulava
  o `flex-wrap` de dentro dele** — por isso o badge da S8 não quebrava sozinho.
- **`RealEstateYieldCard`** — tabela de 5 colunas ganha wrapper rolável.
- **`globals.css`** — degrau dos `text-style-*` de KPI abaixo de 640px, escopado
  a `[data-report-mode]`: 42px de mono pedem ~314px e a caixa útil tem 310px.
- **`report-print.css`** — no papel, `overflow: visible` nos wrappers e quebra
  em `th`/`td` ([[ADR-376]] D3).

## Critério de aceite

- [x] Inventário de vazamento em 390px e 703px: **8 focos → 0** (sobra um
      `span.truncate`, que é ellipsis intencional com affordance).
- [x] Coluna Δ do V0 não se perde em nenhuma largura entre 390px e 1120px
      (varredura de 16 larguras; antes perdia a partir de 691px).
- [x] PDF real inspecionado visualmente, não só pela camada de texto.
- [ ] Gate permanente da classe em `frontend/tests/e2e/reports/` — varredura
      derivada do DOM, com âncora anti-fail-open exigindo `[data-report-section]`
      presente (sem ela, rota que crasha passa verde).
- [ ] Baselines visuais: medir o delta e **olhar** os PNGs antes de rebaselinar;
      regeneração só em runner Linux via dispatch com `run_visual=true`.

## Fora de escopo

- **Medida de linha no papel.** A 703px com corpo em 10pt a prosa fica com
  100–110 caracteres por linha (o confortável é 45–75). É legibilidade, não
  perda de dado — não se resolve com duas colunas, e sim com `max-width` em
  `@media print`. Transferido, sem dono.
- **`hidden md:block` como classe.** Hoje `alocacaoCardParts` e
  `CoberturaSegurosCard` entregam ao papel a variante mobile; nesses dois o dado
  sobrevive porque a variante mobile é completa — por acidente, não por
  desenho. [[ADR-376]] D1 fixa a regra; a varredura dos call-sites existentes
  não entra nesta lane.
