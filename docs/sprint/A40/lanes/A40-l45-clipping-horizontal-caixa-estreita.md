---
id: A40.l45
type: lane
title: "Clipping horizontal em caixa ≤700px: o dado sai do relatório sem deixar rastro"
sprint: A40
status: shipped
priority: P1
branch_slug: a40-l45-clipping-horizontal-caixa-estreita
adrs:
  - "[[ADR-381]]"
  - "[[ADR-076]]"
  - "[[ADR-129]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/frontend
  - area/design-system
  - area/report
---

# A40.l45 — `clipping-horizontal-caixa-estreita`

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

## Desfecho — ✅ shipped

Mergeado em `main` no commit `70407cc3` ([PR #1387](https://github.com/davidrobert/mathoms/pull/1387)),
2026-08-12. `All checks green` verde. O job `Frontend visual snapshots` fica
vermelho por passivo herdado + flakiness do `S2` — medido e explicado no
§Follow-up; **nenhum dos 6 snapshots que ele acusa difere desta branch para
`main` puro**, exceto o `S2`, cuja variação é do próprio gate.

## Escopo

Entregue no commit `37ba3af4`. Cada mudança tem causa própria — não é um
`min-w-0` espalhado:

- **`ReportSection`** — `grid-cols-1` explícito. O track era `auto` e crescia
  até o `max-content` do filho mais largo, arrastando os irmãos; como vale
  abaixo de 768px, atingia o PDF inteiro ([[ADR-381]] D5). **Sem `min-w-0` nos
  filhos**: ver §Regressão 2.
- **`VariacaoSection` (V0)** — tabela vira lista rótulo/valor abaixo de `sm:`
  (640px, não 768px: a caixa A4 receberia a pilha sem precisar), com cor, glifo
  e `aria-label` preservados juntos ([[ADR-381]] D4). O rótulo passa a quebrar e
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
  em `th`/`td` ([[ADR-381]] D3).

## Critério de aceite

- [x] Inventário de vazamento em 390px e 703px: **8 focos → 0** (sobra um
      `span.truncate`, que é ellipsis intencional com affordance).
- [x] Coluna Δ do V0 não se perde em nenhuma largura entre 390px e 1120px
      (varredura de 16 larguras; antes perdia a partir de 691px).
- [x] PDF real inspecionado visualmente, não só pela camada de texto.
- [x] Gate permanente em `overflow-horizontal.@critical.spec.ts` — varredura
      derivada do DOM, âncora anti-fail-open exigindo `[data-report-section]`.
      **Provado por mutação**, não por estar verde: revertido o `grid-cols-1`, o
      gate acusa 239px em S3 e 132px em S4; revertido o `hidden sm:table`, acusa
      a tabela visível no telefone.
- [x] Baselines visuais: **nenhum rebaseline por conta desta lane**. Medido com
      o controle rodado duas vezes (branch cortada de `origin/main`, job visual
      via dispatch): o `main` de 2026-08-12 **já falha** em 6 snapshots
      (`S2` ×2, `S3` ×2, `APP_A`, `S_parecer retido`) — passivo dos PRs recentes,
      que não rodam o job (é opt-in por label). Comparando os `actual` dos dois
      runs **no mesmo runner**, S3/APP_A/S_parecer dão **0 px** de diferença
      entre `main` e esta branch. A S2 dava 9,5% e foi corrigida — ver §Regressão 2.
- [x] `print.@critical` (diff de pixel do PDF) falha **localmente** com 19.133px
      contra tolerância de 500 — e falha com o **mesmo número** no código
      pré-fix. É divergência macOS × baseline de runner Linux; o fix não muda um
      pixel dessa página. Quem decide é o CI.

## Regressão 1 — o `anywhere` partia número no papel

O primeiro commit fechou o vazamento e **abriu** um defeito mais sutil, pego só
porque a verificação leu o PDF real em vez de confiar na tela: `overflow-wrap:
anywhere` aplicado a `th`/`td` partia a célula Δ em `"52,0"` + `"%"` em linhas
diferentes. O valor seguia impresso e, ainda assim, uma busca por `52,0%` no PDF
não o achava — que é como um terceiro lê o arquivo. Corrigido em `abf93169`:
quem encolhe a tabela é o rótulo; número é átomo.

## Follow-up com evidência — `S2` é flaky no gate visual → [[A40.l53]]

Medido no run 31576243325: as **três tentativas do mesmo job**, mesmo commit,
mesmo runner, diferem entre si em **5,1%, 5,6% e 6,3%** no `S2-dark`. A
tolerância do spec é 2,5%, então esse snapshot reprova sozinho em qualquer PR
que aplique o label `visual` — e de fato reprova em `main` puro.

Não é ruído de antialiasing (que fica muito abaixo de 1%): é o Chart.js
desenhando estados diferentes a cada render. O `setupReport` espera
`waitForTimeout(500)`, e a animação do canvas só estabiliza entre ~900ms e
~1200ms (medido por hash do `getImageData` em instantes crescentes) — a captura
cai dentro da animação.

Tentei fechar isso dentro desta lane trocando a espera fixa por espera até o
canvas estabilizar, e **reverti**: a espera por estabilidade não eliminou a
variação (o hash amostrado estabiliza antes do desenho terminar), e manter código
apoiado numa hipótese que a própria medição derrubou é pior que não ter.
Quem pegar precisa começar por aqui, não pelo timeout.

Enquanto não for resolvido, o job é **fail-open na prática**: some no ruído a
capacidade de distinguir regressão real. Foi só comparando os `actual` de dois
runs **no mesmo runner** que deu para separar o que era desta lane (S2-light,
9,9% → 0px) do que já estava em `main` (S3, APP_A, S_parecer: 0px de diferença).

## Fora de escopo

- **Medida de linha no papel.** A 703px com corpo em 10pt a prosa fica com
  100–110 caracteres por linha (o confortável é 45–75). É legibilidade, não
  perda de dado — não se resolve com duas colunas, e sim com `max-width` em
  `@media print`. **→ [[A40.l55]]** (aberta 2026-08-12).
- **`hidden md:block` como classe.** Hoje `alocacaoCardParts` e
  `CoberturaSegurosCard` entregam ao papel a variante mobile; nesses dois o dado
  sobrevive porque a variante mobile é completa — por acidente, não por
  desenho. [[ADR-381]] D1 fixa a regra; a varredura dos call-sites existentes
  não entra nesta lane. **→ [[A40.l54]]** (aberta 2026-08-12).

## Regressão 2 — `min-w-0` desalinhou o gráfico, e só no Linux

O job visual acusou S2 (light + dark) com **9,185%** de pixels divergentes,
contra tolerância de 2,5%. Minha primeira leitura foi "baseline desatualizada,
passivo herdado" — **errada**. O que decidiu foi o **controle**: disparar o mesmo
job a partir de uma branch cortada de `origin/main` puro. Ele passou **verde**,
logo a falha era da lane.

O mecanismo só aparece no runner Linux: com `[&>*]:min-w-0` no grid, o card do
gráfico passa a poder encolher abaixo do seu `max-content`; as barras do Chart.js
ficaram **comprimidas à esquerda enquanto os rótulos do eixo seguiam até a
direita** — gráfico desalinhado do próprio eixo, pior que o defeito que a lane foi
corrigir. Em macOS a divergência era de 0,063% (só os FABs flutuantes), então
medir só na minha máquina teria deixado passar.

Duas rodadas até fechar, e a primeira atribuiu a causa errada:

1. Removi `[&>*]:min-w-0` do grid — o gate seguia 6/6 sem ele (o `grid-cols-1`
   explícito sozinho fecha a classe), mas **a S2 continuou divergindo ~9,5%**.
2. O culpado era o **header do `ReportCard`**: `flex-wrap` + `min-w-0` aplicados
   em **toda** largura. O header recalculava a caixa depois de o Chart.js
   desenhar, e as barras ficavam comprimidas à esquerda com o eixo esticado até
   a direita. Escopado para `max-sm:`, a S2 em 1280px volta a **0 px** de
   diferença contra `main` — mesmas dimensões — e o gate de 390px segue 6/6.

Regra que fica: mudança motivada por caixa estreita entra com `max-sm:`. Aplicar
"de graça" em toda largura parece inofensivo e não é — o desktop tem canvas, e
canvas não perdoa recálculo de caixa depois do render.

**Lições que valem além desta lane:**

1. **`cmp` byte a byte em PNG é falso positivo** — dois encodes da mesma tela
   diferem em bytes com **zero** pixel diferente. Foi o que me fez classificar
   S1/S2/S3 como "ruído de canvas". Meça por pixel (limiar ~8/255) e olhe a
   **caixa** da diferença: foi ela que mostrou que a mudança de 0,063% em macOS
   era chrome flutuante, não o gráfico.
2. **Diferença de plataforma não é só antialiasing.** Uma regra de layout
   sensível a largura de fonte pode mudar de comportamento entre macOS e Linux.
   Medir pré/pós na própria máquina responde "o que MUDOU aqui", não "o que o
   gate vai ver".
3. **O controle em `main` puro é o instrumento que decide** de quem é a falha.
   Custa um dispatch de workflow e substitui qualquer argumentação.
