---
id: ADR-378
type: adr
title: "O PDF é uma caixa de 703px: `md:` não é o teste de \"é celular\" no relatório"
status: Decidido
date: "2026-08-11"
relates_to: ["[[ADR-076]]", "[[ADR-129]]", "[[ADR-236]]", "[[ADR-372]]"]
tags:
  - type/adr
  - status/decidido
  - area/frontend
  - area/design-system
  - area/report
---

# ADR-378 — O PDF é uma caixa de 703px

## Contexto

O relatório tem **três** superfícies, não duas: a tela do desktop, o telefone e
o **papel**. O papel é a única que sai do produto para terceiros (contador,
corretor, banco) e a única que o cliente arquiva.

Ao gerar o PDF, o Chromium relayouta contra a **caixa de página**, não contra o
viewport da janela. Com A4 retrato e as margens de
[`pdf_renderer.py`](../../backend/app/services/pdf_renderer.py) (15/12/15/12mm),
a largura útil é **703px**. Consequência que estava implícita e custava dado:

- `md:` (768px) **nunca casa no PDF**. Toda regra `md:` escrita como "isto é
  desktop" entrega ao papel a variante de celular — incluindo `hidden md:block`,
  que remove do PDF a tabela que o autor pensava estar imprimindo.
- `sm:` (640px) **sempre casa no PDF**. É o divisor certo entre "papel e
  desktop" de um lado e "telefone" do outro.

A medição que originou a decisão (2026-08-11, sonda de vazamento derivada do DOM
sobre 3 fixtures × 3 superfícies) encontrou a classe em dois regimes distintos:

| superfície | caixa útil | sintoma |
| --- | --- | --- |
| telefone 390px | 310px (o `px-10` do `<article>` come 80px) | coluna Δ do V0 **301px fora** da caixa, hero 53px, resumo de seção 263px |
| papel 703px | 703px (o print CSS zera o padding) | cabia, com **12px de folga** — a tabela do V0 exigia 691px |

Os dois números importam por motivos opostos. No telefone o dado era
**inalcançável**: `document.scrollWidth == innerWidth`, ou seja a página não rola
horizontalmente, então o que passa da borda não é "cortado feio", é perdido. No
papel não havia defeito visível — havia **12px separando o relatório do
precipício**, sem nada que gateasse a distância.

## Decisão

**D1 — `sm:` (640px) é o divisor papel/desktop × telefone.** Variante que o
papel deve receber usa `sm:`; `md:` fica para diferenças genuínas entre desktop
largo e o resto. `hidden md:block` sem par mobile equivalente é defeito: some do
PDF sem erro e sem sinal.

**D2 — O que o papel faz de diferente da tela é declarado em `@media print`,
não herdado da cascata de breakpoints.** Precedente literal do mockup aprovado
([`EXEMPLO_DE_RELATORIO.html:679`](../plan/REPORT_PREMIUM/EXEMPLO_DE_RELATORIO.html)
declara `grid-template-columns` para impressão em vez de contar com o `md:`).
Corolário: **não** trocar `md:grid-cols-2` por `sm:grid-cols-2` para ganhar duas
colunas no papel — isso mexe na tela de 640–767px, onde dois cards de ~292px com
gráfico viram ruído. Piso medido para 2-up em relatório financeiro impresso:
~300px por card rótulo/valor, ~420px por card com gráfico ou tabela ≥3 colunas;
a 703px com gap de 24px duas colunas dão 339px — legítimo só para KPI.

**D3 — `overflow-x: auto` não é contenção no papel.** Em papel não existe gesto
de rolagem: o wrapper apenas deixa de pintar o que passa da caixa, e a coluna
some do arquivo que o cliente arquiva. Vale como affordance **de tela**; o
`report-print.css` devolve `overflow: visible` e faz o conteúdo caber por quebra
(`overflow-wrap: anywhere` em `th`/`td`), nunca por `table-layout: fixed` — sem
`<colgroup>` ele divide as colunas igualmente e parte valores monetários, que
são strings inquebráveis.

**D4 — Tabela que não cabe vira lista rótulo/valor abaixo de `sm:`, preservando
cor, glifo e `aria-label` juntos.** Variante que perde um dos três é perda de
acessibilidade disfarçada de responsividade ([[ADR-372]] estabeleceu que cor e
nome acessível caem juntos).

**D5 — Filho de grid declara `grid-cols-1` explícito.** Sem ele o track é `auto`
e cresce até o `max-content` do filho mais largo, arrastando **todos** os
irmãos. Como o efeito vale abaixo de 768px, ele atinge o PDF inteiro — foi o que
empurrava o resumo editorial de seção para fora da caixa em S3 e S4.

## Consequências

- O gate da classe é a sonda de vazamento derivada do DOM (todo nó cuja borda
  direita passa a do `<article>`, ignorando o que esteja dentro de contêiner
  rolável), rodada nas duas superfícies estreitas. Varredura **derivada**, não
  lista de seletores: componente novo cai no gate sozinho — a lição do
  `print-chrome.@critical`, cujo inventário de chrome é derivado pelo mesmo
  motivo.
- Medir print exige `emulateMedia({media:"print"})` **e** viewport na caixa de
  página. Um sem o outro mede outra coisa (precedente: A40.l22, em que medir a
  1280px escondia exatamente os dois controles que apareciam no PDF).
- `break-inside: avoid` continua proibido em bloco cuja altura depende do volume
  de dados do usuário — regra que já vivia em `report-print.css` e que o card do
  V0 contrariava com `style` inline, que vence a folha.
- O degrau tipográfico dos `text-style-*` de KPI abaixo de 640px vive em
  `globals.css` escopado a `[data-report-mode]`: `tokens.css` é **gerado** por
  `design-tokens/build.py` e o schema de `text_styles` não expressa media query.
  Call-site que dimensiona com utilitário Tailwind (`text-3xl`) precisa do seu
  próprio degrau — o override por classe não o alcança.

## Alternativas consideradas

- **Δ como sufixo da coluna "Depois" no telefone** — rejeitada: Δ é a coluna do
  julgamento e o valor de scan vertical é comparar magnitude *entre*
  indicadores; virar sufixo destrói esse eixo, e resolve um problema que no papel
  não existe.
- **Só `overflow-x: auto` na tabela** — rejeitada: scroll horizontal aninhado em
  scroll vertical é descoberto por poucos, some do screenshot que o usuário
  compartilha e vira clip silencioso quando alguém imprime a partir da tela.
- **Reduzir a margem física do PDF para ganhar largura** — deferida: a margem é
  decisão de página e vive num lugar só (`pdf_renderer.py`, espelhado em
  `A4_PRINT_PARAMS`/`PRINT_AREA_PX`). Mexer nela para acomodar layout criaria
  dois botões para a mesma mancha gráfica.
