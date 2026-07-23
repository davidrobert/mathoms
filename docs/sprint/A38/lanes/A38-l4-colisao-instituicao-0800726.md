---
id: A38.l4
type: lane
title: "Colisão de instituição: pattern caixa `0800 726` casa SAC Santander com conf 1.0"
sprint: A38
status: shipped
ship_date: "2026-07-23"
ship_pr: 1023
priority: P1
branch_slug: a38-l4-colisao-instituicao-0800726
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a38
  - status/shipped
  - priority/p1
  - area/backend
  - area/pipeline
---

# A38.l4 — `colisao-instituicao-0800726` (achado #3)

## Problema (evidência verificada 2026-07-22)

Em `backend/app/services/classification/institution_classifier.py`, o pattern
da Caixa inclui a alternativa `0800\s*726` (central de atendimento CEF). O SAC
Libras do **Santander** é `0800 726 0322` — mesmo prefixo. No corpus local, o
extrato consolidado Santander de um mês classificou `caixa` com **conf 1.0**,
o que **impede o LLM fallback de corrigir** (só roda com conf < 0.8): o erro é
determinístico e terminal. O mês anterior só acertou `santander` porque a
âncora "JUROS SALDO UTILIZ ATE LIMITE" apareceu no preview de 5000 chars — o
layout consolidado não tem nenhuma âncora Santander confiável no pattern
atual (não contém "BANCO SANTANDER" nem "Central de Atendimento Santander"
no texto extraído).

## Escopo

- Restringir a alternativa da Caixa aos ramais canônicos
  (`0800 726 0101|0104`) **ou** exigir co-ocorrência com marcador `CAIXA` no
  preview — decidir na implementação pelo que preservar os fixtures atuais.
- Adicionar âncoras Santander presentes no layout consolidado: código de
  template `Extrato_PF_A4_Inteligente` e/ou cabeçalho
  `EXTRATO CONSOLIDADO INTELIGENTE` (co-ocorrendo com `santander.com.br`),
  posicionadas na entrada `santander` existente (ordem da lista preservada).
- Teste de regressão antes do fix: preview sintético com `0800 726 0322` +
  marcador santander deve classificar `santander`; preview CEF real-like
  (`Alô CAIXA`, `0800 726 0101`) continua `caixa`.

## Critério de aceite

- Corpus local (harness [[A38.l1]]): **os dois** consolidados Santander →
  `institution=santander` determinístico (KR-B).
- Suíte de classification existente verde; nenhum doc do corpus de testes
  muda de instituição (KR-E).

## Risco

Baixo. Pattern change cirúrgico; anti-regressão coberta pelos testes de
classification existentes + corpus.
