---
id: A42.l17
type: lane
title: "Um parser de banco chama o SDK LLM fora do contrato, e a saída livre vira chave de junção"
sprint: A42
status: planned
priority: P0
branch_slug: a42-l17-parser-chama-llm-fora-do-contrato
owner: data-engineer
depends_on: []
adrs: ["[[ADR-173]]", "[[ADR-287]]"]
tags: [type/lane, sprint/a42, status/planned, priority/p0, area/dados, area/llm]
---

# A42.l17 — `parser-chama-llm-fora-do-contrato`

> **Origem:** `R1` da **U3** ([[LEDGER-CERTIFY-active]] §r7). Cético: `PARCIAL`, Crítico → Alto,
> **com escalação que a lente não viu**.

## O defeito

Um parser de banco instancia o SDK do provider **direto** e chama o modelo **sem
`temperature`** (o default do SDK é o valor mais alto), sem seed, sem cache, sem contrato
tipado — e **sem escrever na tabela de telemetria LLM** que é a fonte única declarada. A
descrição que o modelo devolve alimenta a **chave natural** da transação.

## Evidência medida

Sobre o **mesmo documento**, em quatro runs consecutivos, mudaram **2, 1 e 4** de 8 chaves
naturais (25% · 12,5% · **50%**). No corpus E2 inteiro — 136 unidades, 7.991 transações — as
**quatro** chaves que mudaram entre os dois últimos runs estão **todas nesta única unidade**,
a única cujas notas declaram extração por LLM. A tabela de telemetria não tem **nenhuma**
linha para este documento, enquanto tem para 13 outros.

## Blast radius hoje = 0, e isso é o que rebaixa a severidade

Nenhum override vivo casa com as chaves que churnaram. O dano está no **mecanismo**: uma
chamada LLM não-determinística, não-logada e fora do contrato de custo alimentando
identidade de lançamento.

**Medição que reescalaria para Crítico:** um override vivo cuja chave case com transação
desta unidade.
