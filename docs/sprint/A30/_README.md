---
id: MOC-sprint-a30
type: moc
title: "Sprint A30 — Ops FinOps: budget LLM editável no console interno"
aliases: ["A30", "Sprint A30"]
sprint_status: current
date: "2026-07-06"
theme: "ops-finops"
---

# Sprint A30 — Ops FinOps: budget LLM editável no console interno

> **Status:** `current` (aberta 2026-07-06). 1 lane. Origem: dogfood do owner
> em 2026-07-06 — run do pipeline (executor Go, F2 do ADR-150) abortou no
> hard-stop de budget LLM ([[ADR-173]]: cap $5, gasto $5.57 = 111% ≥ 110%) e
> o único unblock disponível foi `UPDATE` manual via SQL no DB. Co-design
> 2026-07-06: `product-manager` (P1 por WSJF, critérios de aceite, janela
> mês-calendário vs rolling) + `sre-devops` (guardrails FinOps: uncap
> explícito, teto de sanidade, audit hard-fail, não invalidar cache Redis).
> Sem ADR nova — conformidade operacional a [[ADR-116]] + [[ADR-173]].

## Lanes

| Lane | Título | Prioridade | Status |
|---|---|---|---|
| [[A30.l1]] | Editor de budget LLM por workspace no console ops | P1 | ready |

## KR

- **KR1:** 0 unblocks de budget via SQL manual após a lane (operação vira
  UI + audit). Verificação: trilha `workspace.update_llm_budget` no audit
  log passa a existir; nenhum novo incidente de UPDATE direto.
