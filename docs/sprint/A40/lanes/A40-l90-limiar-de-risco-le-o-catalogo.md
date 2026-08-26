---
id: A40.l90
type: lane
title: "A superfície determinística de risco tem quatro regras hard-coded e não lê o catálogo canônico de limiar"
sprint: A40
plan: PLAN-deterministic-authority
status: blocked
priority: P0
branch_slug: a40-l90-limiar-de-risco-le-o-catalogo
owner: financial-planner
depends_on:
  - "[[A40.l89]]"
adrs:
  - "[[ADR-399]]"
  - "[[ADR-416]]"
tags:
  - type/lane
  - sprint/a40
  - status/blocked
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l90 — `limiar-de-risco-le-o-catalogo` (PV9-06)

> **Origem:** rodada unificada **U1** 2026-08-26 ([[ADR-416]]) ·
> [[PIPELINE-REVIEWS-active]] §r9 — **PV9-06** (Alto, P0).
> Cru + síntese: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

> **Muta E5 ⇒ zera o contador de 2 re-runs.** Serializada atrás da [[A40.l89]]; a ordem é
> forçada, não preferência — ver §Fora de escopo lá.

## O fato, medido (2026-08-26)

[`PontosUrgentesAnalyzer.analyze`](../../../../pipeline/domain/services/pontos_urgentes_analyzer.py)
é a superfície determinística de risco e tem **quatro regras hard-coded**: reserva abaixo do
mínimo, endividamento acima do máximo, gap de seguro de vida, rentabilidade não apurada.
**Nenhuma consulta `kpi_targets`.**

Concentração imobiliária, desvio de alocação-alvo e exposição cambial **não têm regra**. No
run da rodada, três limiares com procedência `limiar_canonico` estavam rompidos e a
superfície publicou **um** ponto urgente — o de proteção, que é uma das quatro regras fixas.

E o catálogo canônico ([[ADR-399]], declarado *"leitor único de cada limiar"*) é **órfão**:
existe no tipo gerado e em **nenhum** componente. O limiar existe, é versionado, tem
procedência declarada — e não chega a superfície nenhuma.

## O que a medição já descartou

- ~~"`alertas` é a superfície determinística de risco e está vazia com três limiares
  rompidos"~~ — **refutado pelo cético**: [`build_alertas`](../../../../pipeline/domain/services/e5_serialization.py)
  tem três condições e **nunca** carregou limiar de KPI; o docstring declara que lista vazia
  é *empty state honesto*, por curadoria da [[A40.l7]]. **Alvo errado.** O alvo certo é
  `pontos_urgentes`.
- ~~"o tier esconde o parecer do Free, então o Free não vê risco nenhum"~~ — **refutado**: o
  Free recebe diagnóstico + 3 pontos fortes + **1 risco** (o de severidade máxima).

## A pergunta que esta lane decide

A [[ADR-399]] §D4 **isenta explicitamente** os leitores pré-existentes (*"os leitores
pré-existentes citados em D4 permanecem"*). Estender o leitor único à superfície de risco é
mudança de escopo de ADR `Decidido`.

**Duas leituras:**

| | Leitura | Consequência |
|---|---|---|
| **A** | As regras de risco passam a derivar do catálogo; a isenção da D4 é estreitada | Um limiar, um lugar. Muda o que dispara ponto urgente ⇒ delta de golden |
| **B** | A isenção permanece e as regras ganham as três dimensões faltantes hard-coded | Não mexe na ADR, e reintroduz o problema que a D4 existe para resolver |

**Defendo A**, e a forma é **emenda datada à [[ADR-399]] no PR1**, com a taxa de disparo
medida sobre os runs de referência **declarada antes do flip** (doutrina WARN-first de
[[ADR-357]]/[[ADR-358]]). Sem a emenda, a lane viola por omissão uma decisão vigente.

## Escopo

1. **PR1 — emenda datada da [[ADR-399]]**, estreitando a isenção da D4 à superfície de risco,
   com a taxa de disparo medida e escrita.
2. As quatro regras passam a derivar limiar do catálogo.
3. As três dimensões sem regra (concentração imobiliária, desvio de alocação, exposição
   cambial) ganham regra que **lê** o catálogo, não que fixa número.
4. Invariante: `count(kpi_targets rompidos) > 0 ⟹ len(pontos_urgentes) > 0`. Falha hoje.

## Fora de escopo

- O alvo republicado pelo parecer → [[A40.l89]], que vai na frente.
- O denominador de cada limiar (que base cada número mede) → [[A40.l80]], entregue, com
  resíduo declarado.

## Critério de aceite

- O invariante do item 4 é teste e falha por mutação: romper um limiar canônico sem emitir
  ponto urgente ⇒ vermelho.
- A emenda da [[ADR-399]] traz `amended_at` e blockquote de sinal (gate
  `check_adr_amendment_signal`).
- Delta de golden declarado; a taxa de disparo pós-flip bate com a medida no PR1.
- Concluído = PR mergeado em `main` com CI verde.
