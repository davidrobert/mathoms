---
id: A40.l107
type: lane
title: "A conversão tabela→cartão no mobile é aplicada por componente, não por regra: 11 tabelas largas não convertem, e há um terceiro comportamento não previsto"
sprint: A40
status: open
priority: P2
branch_slug: a40-l107-conversao-tabela-cartao-por-componente
owner: product-designer
depends_on: []
adrs: []
tags: [type/lane, sprint/a40, status/open, priority/p2, area/frontend]
---

# A40.l107 — `conversao-tabela-cartao-por-componente`

> **Origem:** `RR8-02` da rodada unificada **U4** ([[REPORT-REVIEWS-active]] §r8).
> **CONFIRMADO** pelo cético, que corrigiu a contagem **para cima**.

## O defeito

A conversão de tabela para cartão no mobile existe e funciona — mas é aplicada
**componente a componente**, não por regra. Medido por diff dos cabeçalhos
tab-separados entre as duas viewports:

- **4 convertem**: indicadores de "O que mudou", endividamento, detalhe por imóvel, alocação.
- **11 com ≥3 colunas não convertem** (o enunciado original dizia ≥6 — o cético mediu mais),
  incluindo as **3 mais largas** (7, 6 e 6 colunas).
- **Um terceiro comportamento, não previsto por nenhum dos dois:** o ranking de ativos
  **nem converte nem preserva** — descarta uma coluna e segue tabela.

## Caveat declarado

Overflow horizontal **não é observável** em dump linearizado. Se a medição de
`scrollWidth > clientWidth` nas 3 tabelas largas em 390px não acusar overflow, o defeito é
só de **consistência de padrão** e a severidade cai para Baixo. Essa medição é
pré-requisito do fecho, não do início.

## Critério de aceite

- [ ] O comportamento responsivo de tabela é decidido por **regra** (largura, nº de
      colunas, densidade) e não por escolha caso a caso.
- [ ] O terceiro comportamento (descartar coluna e seguir tabela) some, ou é declarado
      como estratégia legítima com o critério que o dispara.
- [ ] **Medição de fecho:** `scrollWidth > clientWidth` em 390px nas tabelas que hoje não
      convertem.

## Relação com a coluna descartada

A supressão de coluna no mobile é da [[A40.l108]]? **Não** — é `RR8`/`C1`, triado
`MEDIÇÃO-DE-CONHECIDO` de `RR6-23` e **não** abre lane aqui. Esta lane é sobre o **padrão
de conversão**, não sobre qual coluna cada tabela escolhe perder.
