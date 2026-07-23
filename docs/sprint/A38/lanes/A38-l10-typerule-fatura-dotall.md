---
id: A38.l10
type: lane
title: "TypeRules genéricas de fatura nunca cruzam linha (gaps `.{0,N}` sem re.DOTALL)"
sprint: A38
status: planned
priority: P2
branch_slug: a38-l10-typerule-fatura-dotall
adrs: []
depends_on: []
parallel_with: ["[[A38.l9]]"]
tags:
  - type/lane
  - sprint/a38
  - status/planned
  - priority/p2
  - area/backend
  - area/pipeline
---

# A38.l10 — `typerule-fatura-dotall` (achado #9)

## Problema (evidência verificada 2026-07-22)

As TypeRules `fatura` (genérica, priority 21) e `faturasantander`
(priority 11) em `type_classifier.py` usam gaps `.{0,1200}?`/`.{0,2600}?`
compilados com `re.I | re.MULTILINE` — **sem `re.DOTALL`**, `.` não casa
`\n`, então a âncora ("FATURA", "Cartão de Crédito") e o marcador financeiro
("Total a Pagar", "Vencimento") precisam estar **na mesma linha**. Em PDF
extraído isso quase nunca acontece: **as 6 faturas do corpus (3 Santander +
3 Itaú) deram conf 0.0** — nenhuma passou pelo regex; classificação ficou
100% dependente do LLM.

## Escopo

- Adicionar `re.S` aos patterns com gap multi-linha (ou trocar `.` por
  `[\s\S]`), mantendo as janelas curtas (≤2600 chars) — atenção a
  backtracking: gaps lazy + janela limitada, medir tempo de classify no
  corpus de testes.
- Revalidar a **ordem de prioridade**: com DOTALL, as regras genéricas casam
  mais — garantir que não roubam docs de regras específicas (informes,
  extratos) usando o corpus de classification existente como oráculo.
- Teste de regressão antes do fix: previews sintéticos multi-linha de fatura
  (âncora e marcador em linhas distintas) → conf ≥ 0.8.

## Critério de aceite

- Corpus local (harness [[A38.l1]]): 6 faturas saem de conf 0.0 para
  classificação determinística **≥ 0.8** com o tipo correto (KR-B; decisão do
  painel/pm: 0.7–0.79 ainda aciona o LLM fallback — o limiar que satisfaz
  "sem LLM" é 0.8) — Santander via [[A38.l7]] (específica), Itaú via genérica
  `fatura`.
- Corpus de classification existente: **zero mudança de tipo** em qualquer
  doc hoje bem-classificado (KR-E); tempo de classify sem regressão
  perceptível (mesma ordem de grandeza).

## Risco

Médio-baixo: mudança de semântica em regra genérica — o oráculo de
anti-regressão (suíte de classification) é a proteção; qualquer roubo de
classificação aparece lá.
