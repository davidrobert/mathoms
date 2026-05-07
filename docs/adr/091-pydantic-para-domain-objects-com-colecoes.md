---
id: ADR-091
type: adr
title: "Pydantic para domain objects com coleções"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 091"]
tags:
  - area/backend
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 28
---

# ADR-091 — Pydantic para domain objects com coleções

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 5 / R11

**Contexto:** Python dataclasses frozen só proíbem reassignment — mutação
interna de campos `dict`/`list` ainda é possível (`obj.rules["new"] = "x"`).
Para `StageConfig` (com 7 campos dict), isso é inaceitável.

**Decisão:** Regra de imutabilidade por tipo de objeto:

| Objeto | Escolha | Motivo |
|---|---|---|
| `Money`, `Transaction`, `Investment`, `Baseline`, `ReconciliationConfig`, `CategorizationRules`, `StageSpec` | `@dataclass(frozen=True)` | Campos primitivos + tuples — dataclass suficiente |
| `StageConfig` | `pydantic.BaseModel` + `ConfigDict(frozen=True)` | Campos dict — pydantic deep-copia na construção |
| `BankStatement` | `@dataclass` (não-frozen) | `transactions: list` muta pela lógica do pipeline; invariante documentado |

Services domain (`ReconciliationService`, `CategorizationService`, calculadoras)
consomem os value objects e retornam `@dataclass(frozen=True)` para reports
(`CashFlowReport`, `PatrimonioReport`, etc.).

**Consequências:**
- ✅ Tipos em `pipeline/domain/models/` e `pipeline/domain/services/calculators.py`
  são seguros para compartilhar entre threads.
- ✅ Pydantic frozen bloqueia `model.pipeline = {}` em runtime — `ValidationError`.
- ⚠️ Pydantic adiciona overhead (~100μs/construção) — irrelevante em workloads
  de pipeline (segundos-minutos por stage).
