---
id: A40.l46
type: lane
title: "Resíduos do bloco de identidade (perfil): baseline de print não provada + variant feature sem o DNA do mockup"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l46-residuos-perfil-identidade
adrs:
  - "[[ADR-117]]"
  - "[[ADR-370]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/frontend
---

# A40.l46 — `residuos-bloco-identidade-perfil`

> **Aberta em 2026-08-12**, no fecho da investigação do overlap "A Família" /
> "Titulares" (dogfood `5@5.com`, PR #1382 `ad33d456`). Coleta os **dois achados
> em aberto que nenhuma sessão está atacando** — os demais follow-ups da mesma
> investigação já têm dono (ver §Fora do escopo). Origem: pareceres de
> `product-designer` + `information-architect` (2026-08-11).

## Problema

Dois resíduos da mesma investigação, sem rastro executável até esta lane:

### 1. A baseline visual do PDF não foi provada após dois PRs no mesmo card

O job `frontend-print-visual` é **label-gated** (`print`) e **skipou** em
**quatro** PRs seguidos que mexeram no card ou no CSS de print do relatório:
#1382 (fusão do bloco de identidade, seção `perfil` nova), #1386 (A40.l43,
prosa em `columns-2`), #1387 ([[A40.l45]], clipping — grid de TODAS as
seções) e #1400 (break-before da primeira seção). A análise diz que a página 1 do PDF não muda —
o bloco entra **depois** da quebra que segue o grid de KPIs — mas nenhum runner
Linux verificou. O gate compara **só a página 1** (`report.print.pdf.png`,
`MAX_DIFF_PIXELS 500`), e a última vez que ficou vermelho a causa era ambiental
(fuso "12h00" runner vs "09h00" local + antialiasing macOS≠Linux — diagnóstico
no §Notas do #1382).

Risco de deixar como está: o próximo PR com label `print` herda uma falha que
não é dele, e o diagnóstico se perde no contexto errado.

> **Correção 2026-08-14 — a previsão acima foi medida e é falsa.** O risco
> descrito realizou-se: o `frontend-print-visual` está vermelho em `main` desde
> antes do #1453, e o PR que o herdou não era o causador. A análise de que "a
> página 1 do PDF não muda" no #1400 estava errada — foi o #1400 que a mudou.
> A/B com `pdftotext` (mesma máquina, mesmo fixture, único delta = o hunk de 13
> linhas): com o `break-before: avoid`, a página 1 fica em capa + Premissas (393
> chars) e os 6 KPIs abrem a página 2; sem ele, a página 1 leva os KPIs (1076
> chars). `avoid` é keep-with-**previous** — em vez de puxar S1 para cima, ele
> arrasta o hero para baixo, produzindo justamente a "página nova meio vazia"
> que a regra dizia evitar. Revertido em
> [PR #1458](https://github.com/davidrobert/mathoms/pull/1458), junto com a
> troca do gate de computed style por gate de efeito sobre a página 1 do PDF.
> **Emenda 2026-08-14 (mesma sessão, no closeout): o §Critério de aceite do item
> 1 está satisfeito.** A frase original dizia que o item 1 "continua aberto" —
> impreciso, e a imprecisão é minha. O critério é literalmente *"run do job
> `frontend-print-visual` referenciado nesta lane, verde"*, e o run existe:
> [31823180323](https://github.com/davidrobert/mathoms/actions/runs/31823180323),
> `frontend-print-visual` **success** sobre o tip de `main` `5b4beee6`, com a
> baseline commitada **inalterada** — ou seja, nem a segunda perna do critério
> (baseline nova com PNG inspecionado) foi necessária: a baseline nunca esteve
> errada, o #1400 respondia por 100% da divergência.
>
> O que continua aberto **não é o item 1**, é a política que o §Problema dele
> descreve — o job ser label-gated, de modo que PR sem o label envelhece a
> baseline em silêncio. Essa é a linha `sem lane` do
> [`_README`](../_README.md) da sprint §"Rodar ainda não é gatear", corrigida no
> mesmo PR desta emenda.

### 2. `card-variant-feature` perdeu o DNA do mockup no build de tokens

No exemplo canônico ([[ADR-117]]), `.card-feature` é gradiente + `border-left:
4px`; o token gerado (`tokens.css`) virou borda 1px chapada — num relatório onde
praticamente todo card e todo `SectionSummary` carregam acento de 4px. Foi o
que fazia "A Família" parecer "fora do padrão" antes da fusão. A [[A40.l33]] §3
mediu a perda de forma independente (`--report-gradient-card-feature` é token
**sem consumidor**) e deferiu a decisão de política — "o `report_palette`
espelha o mockup ou reflete o uso?" — para lane própria com a [[ADR-117]] na
mesa. Esta lane é o veículo. `feature` é o **default** do `ReportCard` (69
call-sites herdam): qualquer mudança move baselines visuais em bloco.

## Tarefa

1. **Prova do gate de print** (barata, primeiro): `gh workflow run CI --ref
   <branch descartável cortada de origin/main> -f run_print=true`. Verde →
   registrar o run id aqui e encerrar o item. Vermelho → regenerar **no runner**
   (`-f update_print_baseline=true`), **olhar o PNG** antes de commitar
   (baseline commitada sem inspeção congela estado quebrado — precedente
   [[A40.l22]]/#1290) e abrir PR só com a baseline.
2. **Política do variant `feature`**: co-design `product-designer` (+
   `senior-cto` se a saída tocar o contrato de tokens): decidir entre (a)
   restaurar o gradiente/acento do mockup no token, (b) declarar o flat como
   novo canônico e **emendar a [[ADR-117]]** (emenda datada, gate
   `check_adr_amendment_signal`), ou (c) split do variant (default flat +
   `feature-hero` fiel ao mockup). Executar a decisão com rebaseline visual
   medido e inspecionado (delta antes de rebaselinar, runner Linux).

## Critério de aceite

- Item 1: run do job `frontend-print-visual` referenciado nesta lane, verde —
  ou baseline nova commitada com PNG inspecionado e justificativa no PR.
- Item 2: decisão registrada (token restaurado, emenda à [[ADR-117]], ou
  variant novo) + `dev/check_tint_contrast.py` verde nos dois temas + nenhuma
  baseline visual rebaselinada sem delta medido e inspecionado.

## Fora do escopo (follow-ups da mesma investigação, já com dono)

- **Clipping ≤700px**: **entregue** — [[A40.l45]] (#1387, [[ADR-381]]) fechou a
  classe (grid track `auto` explícito, caixa A4 703px). Correção 2026-08-12: o
  header do `ReportCard` só ficou de fato escopado a `max-sm` em
  [PR #1429](https://github.com/davidrobert/mathoms/pull/1429) (`9ab41aff`) —
  ver [[A40.l45]] §Regressão 2 §Emenda.
- **`report-print.css` `:first-of-type` inerte + cobertura e2e do roster**:
  **entregue** — #1400 (`9dd59380`): par de irmãos `[data-report-section] ~`
  substitui o seletor que contava por tag, com gate de computed style; mock de
  `/config/members` + spec `perfil-roster.@critical` + `perfil` no a11y
  por-seção. Todos os PRs da família skiparam o job de print — daí o item 1.
- **Narrador `perfil_familia`**: **entregue** — [[A40.l43]] (#1386) matou a
  coluna `right` no narrador e no renderer (emenda [[ADR-356]]).

## Baseline de pixel do PDF ficou stale com o #1828 (2026-08-30)

> Trabalho **recebido** por esta lane — o dono é ela. A origem foi o closeout da `A40.l94`,
> já `shipped`; nada volta para lá.

A baseline de pixel do PDF (`frontend/tests/e2e/reports/__snapshots__/report.print.pdf.png`)
ficou **stale** com o #1828: o card "Consumo Consciente" perdeu o KPI "Teto sugerido"
([[ADR-422]] D2), então o PDF renderizado mudou. Medido local: **19.503px** de divergência
contra tolerância de 500.

**Não bloqueia merge** — `print.@critical` é exclusão nominal do "Report render gate"
(baseline OS-específica), e `print-chrome`/`print-text`, que medem conteúdo e não pixel,
seguem dentro e passam. **Não rebaselinar local**: a baseline nasce no runner Linux/UTC e o
macOS diverge por fuso e antialiasing. Regeneração é `workflow_dispatch` com
`run_print=true` + `UPDATE_PRINT_BASELINE=1` — disparo do dono.
