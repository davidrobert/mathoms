---
id: A38.l8
type: lane
title: "Extrato Consolidado Inteligente Santander: parse_santander_conta extrai 0 transações"
sprint: A38
status: planned
priority: P1
branch_slug: a38-l8-santander-consolidado
adrs: []
depends_on: ["[[A38.l4]]"]
tags:
  - type/lane
  - sprint/a38
  - status/planned
  - priority/p1
  - area/pipeline
  - area/dados
---

# A38.l8 — `santander-consolidado-inteligente` (achado #4)

## Problema (evidência verificada 2026-07-22)

O "EXTRATO CONSOLIDADO INTELIGENTE" (template `Extrato_PF_A4_Inteligente`,
6 páginas, remessa mensal) tem estrutura diferente do extrato de conta
corrente do IB: seções de movimentação, cartões, investimentos e blocos de
marketing. `parse_santander_conta` (construído para o extrato simples) extrai
**0 transações** dos 2 exemplares do corpus; hoje o artefato vazio passa como
válido ([[A38.l3]] corrige o piso; esta lane entrega a extração).

## Escopo

- Mapear as seções do layout consolidado e implementar extração da **seção de
  movimentação de conta corrente** (transações + saldos), via dispatch por
  layout dentro do caminho santander (o extrato simples continua no parser
  atual). Seções de cartões/investimentos ficam **fora do escopo** desta lane
  (nota no resultado; candidatas a lane futura se houver demanda).
- Se a análise do layout concluir que a extração determinística é inviável
  (ex.: texto sem estrutura utilizável), o fallback aceito é **escalação
  explícita** via contrato da [[A38.l3]] + orientação de produto documentada
  ("suba o extrato simples do IB") — decisão registrada nesta lane, nunca
  0-tx silencioso.
- Fixture sintética PII-zero do layout consolidado (seção de movimentação com
  2 páginas) + teste de regressão antes do fix.

## Critério de aceite

- Corpus local (harness [[A38.l1]]): os 2 consolidados produzem `n_tx > 0`
  com conservação verde, **ou** escalam explicitamente com razão estruturada
  (fallback aceito e documentado) (KR-C).
- `parse_santander_conta` sobre fixtures do extrato simples: output idêntico
  (KR-E).

## Risco

Médio: layout consolidado é o mais heterogêneo do corpus; por isso o aceite
admite o fallback explícito — corretude > cobertura. `depends_on` [[A38.l4]]
(sem a instituição correta, o doc nem roteia para o parser santander).
