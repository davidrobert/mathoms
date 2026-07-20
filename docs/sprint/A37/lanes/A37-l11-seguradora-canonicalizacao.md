---
id: A37.l11
type: lane
title: "Seguradora sem canonicalização: mesma cia com dois codes, count inflado e render cru"
sprint: A37
status: planned
priority: P2
branch_slug: a37-l11-seguradora-canonicalizacao
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p2
  - area/pipeline
  - area/dados
  - area/frontend
---

# A37.l11 — `seguradora-canonicalizacao` (PD-05)

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

Os artifacts E2 do run trazem duas apólices **distintas** (ramos e vigências
diferentes) da **mesma seguradora**, uma com `seguradora: "porto"` e outra
`"portoseguro"` — o LLM de E2 violou a instrução de usar codes do catálogo
(`pipeline/llm/prompts/apolice.py:31,115-116`; `institution_catalog` só tem
`porto` → "Porto Seguro"). Consequências:

- `seguradoras_count=3` quando o correto é 2 — `_seguradoras_count` é set naive
  sobre strings cruas (`pipeline/domain/services/protecao_analyzer.py:365-366`);
  o count não renderiza na UI, mas vaza para telemetria e para o bloco de
  proteção do manifest do parecer.
- Render cru: `ProtecaoApolices.tsx:27` imprime o code minúsculo na coluna
  Seguradora — a mesma cia aparece com dois rótulos na tabela do usuário.

## Escopo

- Canonicalizar no boundary E2→domínio: resolver `seguradora` contra
  `institution_catalog` (match por code; fallback normalizado) antes de contar/
  persistir; code desconhecido → `needs_review` do doc, não string livre.
- Reforçar a instrução do prompt + validação de output (enum dos codes de
  `category=insurance`).
- Display name no frontend via catálogo (nunca o code cru).

## Critério de aceite

- Teste de regressão: payload com `porto`+`portoseguro` → count 2 e um único
  display name (hoje: 3 e dois rótulos).
- Unit do resolver: code fora do catálogo → flag de revisão.
- Tabela de apólices renderiza display names capitalizados (snapshot).

## Risco

Médio: normalização retroativa muda artifacts futuros (não migrar os antigos —
re-run recomputa); coordenar com `data-engineer` se optar por migração.
