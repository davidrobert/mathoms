---
id: A24.l5
type: lane
title: "Data Lineage F3 — walking skeleton: _lineage no patrimônio líquido"
sprint: A24
plan: PLAN-data-lineage
status: blocked
priority: P0
branch_slug: dl-f3-skeleton-patrimonio
adrs:
  - "[[ADR-279]]"
  - "[[ADR-281]]"
depends_on: ["[[A24.l2]]", "[[A24.l3]]"]
parallel_with: []
tags:
  - type/lane
  - sprint/a24
  - status/blocked
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A24.l5 — `dl-f3-skeleton-patrimonio` (walking skeleton · G3)

> **Plano:** [[PLAN-data-lineage]] · Onda 3 (F3). Bloqueada pela F2 (Q2: lineage
> sobre fronteira limpa, refs não-órfãs, 1 rebaseline só). Sprint goal da A24.

## Objetivo (G3 / KR2 1/6)

Equipe localiza a origem do **patrimônio líquido** sem abrir um único arquivo de
stage, via **1 comando CLI**, num run canônico.

## Escopo

| Item | Detalhe |
|---|---|
| Bloco `_lineage` field-level no `patrimonio_calculator` | shape da [[ADR-279]]: `{value (Decimal string), label, transform, rule_ref, edge_type, signals, member_hashes, inputs}`; zero timestamp/UUID; `inputs` sorted; `value` espelhado |
| `pipeline/domain/lineage_registry.py` | **dict literal eager** ([[ADR-281]] B2) — NÃO decorator import-side-effect; registrar em `STATELESS_AUDIT.md §2` |
| `LineageResolver` (`pipeline/domain/services/lineage_resolver.py`) | forward, read-only, **stateless** ([[ADR-111]]); nós `dangling`/`no_lineage`, nunca exceção |
| CLI de localização | 1 comando: campo → árvore até a fonte |
| Gate `dev/check_lineage_refs.py` | resolve `module:qualname` por **import real** + ADR existe |
| Gate `check_lineage_sum` | `Σ amount[member_hashes] == value` (cents int), incl. caso incremental (B8: lookup ancorado ao `run_id`) + tx colapsada por dedup |
| `_lineage` declarado em `e5_analysis.schema.json` | antes/junto do flip→strict (dependência W6-T01) |
| Rebaseline E5 esperado e **auditável** | via `golden_diff` + manifesto `ref`/`adr`/`rationale` (l1) + commit isolado (`check_golden_rebaseline_isolation`) + label `golden-rebaseline` + 2º revisor (G-c) |

## Critério de aceite (G3)

- CLI resolve patrimônio líquido → fonte num run canônico.
- `check_lineage_sum` + `check_lineage_refs` verdes.
- Run 2× → **view-model snapshot byte-idêntico** (NÃO payload E2 bruto — F2-B8)
  + `_lineage` byte-idêntico.
- Invariantes de conservação (incl. por categoria) verdes pós-rebaseline (2ª testemunha).
- Snapshot textual de KPIs no render (G-d) verde.

## Owner

Co-design `senior-cto` + `data-engineer` antes de codar (obrigatório, registrar aqui).
