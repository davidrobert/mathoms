---
id: ADR-416
type: adr
title: "Rodada unificada de certificação e revisão: um run, um painel, um entregável, três registros"
status: Proposto
date: "2026-08-25"
relates_to:
  - "[[ADR-343]]"
  - "[[ADR-302]]"
  - "[[ADR-347]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 416"
  - "rodada unificada"
  - "unified certify review"
  - "namespace de código de achado"
tags:
  - type/adr
  - status/proposto
  - area/docs
  - area/tooling
---

# ADR-416 — Rodada unificada de certificação e revisão

**Status:** Proposto · **Data:** 2026-08-25

> **Flip para `Decidido`** no fecho da primeira rodada `U1`, se a forma sobreviver
> ao contato. Enquanto `Proposto`, o runbook é a única superfície executável e
> nenhuma das convenções abaixo é retroativa.

## Contexto

`ledger-certify`, `pipeline-review` e `report-review` são três instâncias da classe
skill ([[ADR-302]]) que terminam no mesmo artefato por caminhos diferentes: o razão
no grão transação, a execução no grão run, o relatório no grão produto. Encadeá-las
já é o uso natural — as duas últimas declaram o encadeamento no próprio `SKILL.md`.

O que torna o encadeamento **ingênuo** caro e o encadeamento **unificado** barato:

- **O substrato já é compartilhado.** `report-review` invoca os scripts que moram
  em `.claude/skills/pipeline-review/scripts/`.
- **O mapa lente→especialista é idêntico** nas duas skills de revisão, e a
  `ledger-certify` usa um subconjunto dele. Encadear em sequência roda o mesmo
  painel de 5 especialistas até 3× sobre o mesmo payload.
- **A taxonomia de dimensão é a mesma nas três**, por desenho declarado na rubrica
  da `report-review`, exatamente para que um achado migre entre registros sem
  re-rotular.
- **As cegueiras são complementares.** A conservação agregada do run é cega a
  defeito *sum-preserving* (reclassificação entre baldes preserva Σ e os CV passam);
  o grão transação a enxerga. O braço cego do relatório dimensionou alavanca contra
  o produtor por não ter trava; a tabela de vereditos do razão é a trava.

O que **não** é compartilhado, e por isso não se funde: cada registro editorial tem
cadência anti-zumbi própria, e re-tria os seus `procede-aberto` na rodada seguinte.
Registro fundido perde o dono da cadência.

## Decisão

**D1 — Um run, um painel, um entregável.** A rodada dispara **um** run, coleta
**uma** vez, e roda **um** painel de 5 lentes com **eixo primário declarado por
lente** (razão → `data-engineer`; materialidade → `financial-planner`; parecer →
`prompt-engineer`; superfície → `product-designer`; invariante → `senior-cto`).
Braço cego e crítico de completude rodam **uma vez para a rodada inteira** — são
cross-cutting, e triplicá-los reintroduz a duplicação que a unificação remove.

**D2 — Verde é `completed`, e só.** `partial_failure` é terminal e **não** autoriza
análise. Run parcial alimenta as três pernas com achado falso de uma vez, e o custo
de descobrir isso depois é a rodada inteira.

**D3 — Namespace por registro de destino, go-forward-only.** A partir de `U1`:
`LC*` (razão) · `PV*` (execução) · `RR*` (produto). O prefixo é o do **registro
onde a linha aterrissa**, não o da lente que a levantou — senão vira etiqueta de
proveniência e a ambiguidade volta por outra porta.

Os códigos anteriores **não são renomeados**: são identificadores duráveis já
citados em commit e trilha de owner, e o dedup dos registros nunca dependeu do
código (é `(dimensão, evidência-âncora, regra)`). Ficam **qualificados na citação**:
`RV4-07 (PIPELINE §r6)`. Sem isso, `RV4-08` nomeia dois defeitos distintos — e uma
citação cruzada sem qualificador já existe no §r4 do [[REPORT-REVIEWS-active]].

**D4 — Destino tem cardinalidade 1; o desempate é o produtor.** Cada linha carrega
uma coluna `registro`, com exatamente um valor, escolhido por **onde o defeito se
conserta**, não por onde ele aparece. Achado que "pertence a dois" é uma de duas
coisas: um defeito com um sintoma (registra no produtor; o sintoma vira ponteiro
com `triagem: MEDIÇÃO-DE-CONHECIDO`), ou dois defeitos (duas linhas, códigos
próprios, referência cruzada). **Nunca cópia** — cópia produz dois zumbis a fechar.

Achado roteado ao vizinho **migra com o código original** e disposição
`movido de <MOC> §rN`, e **não rearma** o relógio anti-zumbi: entra no destino já
como `procede-aberto` herdado, citando a rodada de origem.

**D5 — Costura por id de rodada, fora do título.** O título `## rN — ws-<uuid8>-<data>`
não muda: é âncora durável e é o que as skills leem para re-triar. O id unificado
`U<n>` entra na **primeira linha do blockquote** das três seções, junto com wikilink
para os MOCs irmãos e o `§rN` textual. `U<n>` é recurso global monotônico alocado
**na escrita** do ledger de rodadas do runbook — menção em prosa não reserva. O cru
durável da rodada é **um único diretório** off-git, citado igual nas três seções.

**D6 — O gate de cobertura vira matriz.** Deixa de ser "toda lente aparece em ≥1
cluster" e passa a ser **dimensão × registro** (7 × 3): cada célula é reivindicada
por ≥1 lente **ou** declarada sem cobertura com motivo escrito. Célula vazia e
silenciosa é o modo de falha que já evaporou metade dos achados de uma rodada —
multiplicado por três.

## Consequências

- O procedimento vive em [runbook](../reference/runbooks/unified_certify_review.md),
  não em track nem em plano canônico: re-executa a cada rodada e nunca é consumido.
- Os três `SKILL.md` continuam válidos e executáveis isoladamente. A rodada unificada
  é um **operador de composição** sobre eles, não um substituto.
- A rodada passa a poder medir três coisas que nenhuma skill sozinha mede: atribuição
  do delta E3 ao canal declarado, determinismo do categorizador sobre o E3 do próprio
  run, e paridade **vetorial** (mês a mês) entre razão e view-model — que é onde o
  defeito sum-preserving aparece depois de o escalar fechar.
- Custo: o painel roda uma vez em vez de até três; o run continua sendo a única perna
  paga.

## Alternativas rejeitadas

- **Renomear os 26 códigos ambíguos.** Quebra identificador citado em commit. O
  próprio [[REPORT-REVIEWS-active]] já pagou essa conta e escolheu começar em `r3`
  em vez de renumerar.
- **Um quarto registro unificado.** O insumo dele seria a união de três filas que já
  se re-triam; não teria o que re-triar. Índice fingindo ser registro, sem dono,
  apodrece.
- **Três painéis sequenciais.** ~3× custo para ~1,15× sinal, porque o mapa
  lente→especialista é o mesmo.
- **Três tabelas no mesmo documento.** Reintroduz priorização por silo — se o P0 do
  razão e o P0 do produto não se ordenam entre si, não houve rodada unificada.
- **Emenda na [[ADR-343]].** Ela é sobre a `pipeline-review`, já passa de 150 linhas
  com densidade justificada e tem uma emenda. Estendê-la para governar três skills —
  uma das quais ela nunca governou — é o mesmo movimento que ela própria recusou ao
  não emendar a [[ADR-302]].
