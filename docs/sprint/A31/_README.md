---
id: MOC-sprint-a31
type: moc
title: "Sprint A31 — Débitos da A30: audit persistido (7B.5) + teto de budget calibrado"
aliases: ["A31", "Sprint A31"]
sprint_status: done
date: "2026-07-07"
theme: "ops-debt"
---

# Sprint A31 — Débitos da A30: audit persistido (7B.5) + teto de budget calibrado

> **Status:** `done` (encerrada 2026-07-07 — 2/2 lanes shipped no mesmo dia:
> l1 #819 · l2 #818; [[ADR-309]] flippada para Decidido no #819). 2 lanes paralelas. Origem: os 2
> débitos registrados na lane [[A30.l1]] (editor de budget LLM, PR #815).
> Co-design 2026-07-07: `senior-cto` (atomicidade na mesma transação, fecha
> conflito com DE/SRE) + `data-engineer` (schema, migration, custo escondido
> nos testes) + `sre-devops` (REVOKE, observabilidade, sem dual-write) +
> `product-manager` (backfill = Won't, KR anti-Goodhart, l2 é lane) +
> `financial-planner` (teto US$ 300). ADR canônica da l1: [[ADR-309]]
> (Proposto). Nota do PM: urgência é de oportunidade (fila vazia + contexto
> fresco da A30), não dor presente — 7B.5 destrava F7F-Remote.

## Lanes

| Lane | Título | Prioridade | Status |
|---|---|---|---|
| [[A31.l1]] | Audit do console interno → tabela `internal_ops_audit` (7B.5, ADR-309) | P1 | shipped (#819) |
| [[A31.l2]] | Calibrar `MAX_SETTABLE_BUDGET_USD` US$ 1.000 → US$ 300 (emenda ADR-173) | P2 | shipped (#818) |

## KR

- **KR1 (l1):** 100% dos fluxos de mutação de operador (15 services + 3
  eventos session-less de login) gravam registro em tabela consultável por
  SQL — medido por teste que enumera os paths, não por "tabela criada".
- **KR2 (l2):** teto do editor de budget com racional de unit economics
  documentado em emenda datada da ADR-173 (não valor inventado).
