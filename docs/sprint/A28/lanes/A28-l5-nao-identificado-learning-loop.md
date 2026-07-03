---
id: A28.l5
type: lane
title: "nao_identificado 23% → <5%: regras via Learning Loop + gate de reclassificação do owner"
sprint: A28
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: nao-identificado-learning-loop
adrs:
  - "[[ADR-186]]"
  - "[[ADR-188]]"
parallel_with:
  - "[[A28.l6]]"
  - "[[A28.l7]]"
  - "[[A28.l8]]"
tags:
  - type/lane
  - sprint/a28
  - status/open
  - priority/p1
  - area/pipeline
---

# A28.l5 — `nao-identificado-learning-loop` (Onda 1 · Should · gate `G-owner-reclassify`)

## Problema

`nao_identificado` é a **maior categoria de despesa** do dogfood `72883bde`:
R$ 401.415,87 (~23% do total de R$ 1,77M). Isso invalida em cascata: orçamento
prospectivo, essencial vs supérfluo (denominador da reserva pós-[[A28.l1]]),
equilíbrio Cerbasi e consumo consciente. Sob Cerbasi, "gastar bem" é
inauditável sem saber onde o dinheiro vai — e o rótulo "Gastador" sobre despesa
opaca pode induzir corte de gasto essencial errado.

## Escopo

**Código autônomo (fecha sozinho):**

1. Análise dos maiores ofensores: agrupar as transações `nao_identificado` do
   dogfood por descrição normalizada/estabelecimento, ranquear por valor
   acumulado (script de análise em `_scratch/`, PII-zero no que virar commit).
2. Regras/keywords novas via Categorization Learning Loop ([[ADR-186]] /
   [[ADR-188]]): promover padrões dos top ofensores a `category_keywords` /
   `categorization_rules` persistidas — respeitando os invariantes do loop
   (override manual sticky, mês fechado imutável, conflito determinístico).
3. Superfície de reclassificação pronta para a rodada do owner: fila de
   `nao_identificado` ordenada por impacto (reusar UI existente do loop; só
   criar o que faltar para a rodada ser viável).

**Gate `G-owner-reclassify` (ação do owner, fora do código):**

4. Rodada de reclassificação dogfood dos ofensores restantes; overrides do
   owner viram regras via loop (promoção já existente).

## Critério de aceite

- Regras novas mergeadas + re-run dogfood mostra **queda mensurável** de
  `nao_identificado` só por regras (reportar % antes/depois no PR).
- KR2 (<5%) avaliado **somente pós-gate** `G-owner-reclassify`; gate não
  executado na janela → lane de código fecha, KR reporta redução por regras
  (não falha a sprint).
- Invariantes do loop preservados: teste de que override manual não é
  sobrescrito por regra nova; mês fechado intocado.
- Nenhuma transação real (descrição/valor) em fixture ou commit — análise fica
  em `_scratch/`.

## Notas

- Rebaixada de P0 (parecer de origem) para **Should** pelo product-manager:
  não é violação de fórmula e o alvo <5% depende de rodada manual — mas é
  pré-condição de credibilidade do diagnóstico Cerbasi ([[A28.l4]]).
- Interação com [[A28.l9]]: enquanto `nao_identificado > 10%`, o banner de
  qualidade sinaliza com CTA para a fila de reclassificação.

## Owner

Agente da lane (código) + owner (gate `G-owner-reclassify`).
