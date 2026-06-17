---
id: A26.l6
type: lane
title: "Telemetria de citação: cobertura (missing_path) vs. correção (value_mismatch) + drift"
sprint: A26
plan: PLAN-data-lineage
status: planned
priority: P1
branch_slug: evidencia-coverage-kpi
adrs:
  - "[[ADR-279]]"
  - "[[ADR-292]]"
depends_on: []
parallel_with:
  - "[[A26.l7]]"
tags:
  - type/lane
  - sprint/a26
  - status/planned
  - priority/p1
  - area/data-lineage
  - area/llm
---

# A26.l6 — `evidencia-coverage-kpi` (Onda 6 · cobertura de citação · Regime A)

> **Plano:** [[PLAN-data-lineage]] §Onda 6. **Sem gate de tráfego** (Regime A —
> telemetria pura sobre estrutura existente). Origem: incidente do parecer
> ([[ADR-292]]). Co-design `product-manager` + `data-engineer` 2026-06-17.
> **Roda ANTES da [[A26.l7]]** — estabelece a baseline contra a qual a cobertura
> de listas é medida.

## Objetivo

Promover a KPIs de produção as sementes que a [[ADR-292]] já plantou: separar
**cobertura** (`missing_path` — prosa cita R$ sem path verificável) de **correção**
(`value_mismatch + whitelist_miss + resolve_null` — citação que resolve errado) e
expor a categoria de **drift** do path coercido (`filter`/`regex_match`/
`recursive_descent`). Hoje isso só existe como `failures_by_layer` em `_meta` +
log PII-safe pontual; não é agregável nem por seção.

## Motivação

O gate da [[A26.l2]] (flip strict) mede "% de pareceres com ≥1 violação" — e a
[[ADR-292]] separou `missing_path` de violação justamente para o gate não reprovar
por *visibilidade*. Sem KPI agregável, esse gate é grep ad-hoc (mesmo débito que a
[[A26.l4]] teve de pagar para `dualread.v1_fallback` no dedup). Esta lane torna o
gate de l2 **auditável** e dá o sinal de drift que teria pego o incidente cedo (modelo
novo emitindo filtros) — em métrica, não em incidente de latência.

## Escopo

- Métrica agregável (logger estruturado `mathoms.llm.parecer_planejador`, com
  `workspace_id` + `run_id`) de `failures_by_layer` **× `item_type`** (a dimensão
  por-seção já existe nas `entries` de `parecer_evidencia.py`; é elevar de detalhe
  para agregado).
- Dimensão de cobertura: `missing_path` reportado à parte (NÃO somado em violação).
- Dimensão de drift: contagem por categoria de path coercido (de `_coerce_jsonpath_or_none`).
- Consultável **sem decriptar** o artifact (artifact é Fernet-encrypted).
- Sem mudança de contrato/ADR (telemetria sobre `_LAYERS`/`entries` existentes). Se
  optar por persistir agregado por-seção em `_meta`, é bump aditivo não-breaking.

## Critério de aceite

- KPI separa cobertura (`missing_path`) de correção (3 camadas) por seção, agregável.
- Categoria de drift de path coercido emitida como dimensão (PII-safe; nunca o valor).
- Sem regressão no OpenAPI snapshot (telemetria não é endpoint).
- Baseline registrada **antes** do merge da [[A26.l7]] (para provar que a cobertura
  de listas reduz `missing_path`).
- Instrumenta o gate da [[A26.l2]] e a auditabilidade do **KR3**.

## Owner

Agente da lane; co-design `data-engineer` (contrato de telemetria) + `prompt-engineer`
(observabilidade de prompt/drift).
