---
id: A38.l11
type: lane
title: "Fuzzy-dupe cruza-flagga extratos de moedas distintas do mesmo período (Wise USD × BRL)"
sprint: A38
status: planned
priority: P2
branch_slug: a38-l11-fuzzy-dupe-moeda
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a38
  - status/planned
  - priority/p2
  - area/backend
---

# A38.l11 — `fuzzy-dupe-moeda` (achado #10a)

## Problema (evidência verificada 2026-07-22)

`backend/app/services/documents/document_duplicates.py` marca
`possible_duplicate_of_id` + `needs_review` para o triple
`(DocumentType, bank_code, period)`. Extratos Wise **USD e BRL do mesmo
período anual** são contas diferentes em moedas diferentes, mas têm o mesmo
triple (`bank_statement`, `wise`, mesmo range) → cross-flag falso-positivo,
fricção de review para o usuário e risco de dismissal errado. Com a
[[A38.l6]] entregue, o `e0_doc_type` passa a discriminar
(`extratocontausd` × `extratocontabrl`) — o dedupe é que ainda não usa.

## Escopo

- Incluir discriminador de subtipo/moeda na chave do fuzzy-dupe quando
  disponível: `e0_doc_type` (ou moeda derivada dele) além do
  `DocumentType` — dois docs só se cross-flagam se o subtipo coincidir
  (ou for desconhecido em ambos, comportamento atual preservado).
- Recompute é função pura sobre o workspace — sem migração de dados; rodar o
  recompute nos testes com docs sintéticos.
- Teste de regressão antes do fix: dois docs `bank_statement`/`wise`/mesmo
  período com subtipos `usd`×`brl` **não** se flagam; mesmo subtipo com hash
  diferente **continua** flagando (contrato atual).

## Critério de aceite

- Units acima verdes; suíte de documents existente verde (KR-E).
- Fluxo real validado no harness/upload local: subir os 2 extratos Wise não
  gera `possible_duplicate_of_id` cruzado (KR-B de UX). **Nota do painel/pm:**
  o código shipa independente, mas este aceite de corpus só é verificável
  **pós-[[A38.l6]]** (é ela que faz o subtipo `usd`/`brl` existir) — antes
  disso a lane degrada ao comportamento atual, sem dead code novo.

## Risco

Baixo. Chave mais específica só **remove** falso-positivo; o caso "mesmo
subtipo" mantém o comportamento. Sequenciar após [[A38.l6]] dá o
discriminador de graça (não é `depends_on` duro: a chave pode cair para o
comportamento atual quando o subtipo não existe).
