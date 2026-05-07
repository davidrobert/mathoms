---
id: A8.3
type: lane
title: "TRS real — Carteira de renda + Taxa de Retirada Sustentável efetiva (S7)"
sprint: A8
status: shipped
branch_slug: a8-trs-real
ship_date: "2026-05-05"
ship_pr: 42
adrs: ["[[ADR-164]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a8
  - status/shipped
---


# A8.3 — TRS real — Carteira de renda + Taxa de Retirada Sustentável efetiva (S7)

> Migrada de tabela em `## Sprint A8` do BACKLOG (F4.A.followup, ADR-182).

## Contexto da tabela original

- **Depende de:** A7 ✅ + A8.2 ✅
- **Branch slug:** `a8-trs-real`

## Status (legado)

✅ entregue 2026-05-05 — PR-B [#42](https://github.com/davidrobert/mathoms/pull/42) (aluguel→capital) + PR-A [#43](https://github.com/davidrobert/mathoms/pull/43) (Calculator+ratios, 31+21 tests) + PR-C [#44](https://github.com/davidrobert/mathoms/pull/44) (wire+UI+ADR-164 + 33 Vitest na matriz 18 cenários). 3 fases × 3 agentes paralelos/sequenciais. Tempo total ~5h wall-clock, ~95min trabalho ativo do agente C. ADR-164 "Carteira de renda e TRS efetiva" Decidido.
