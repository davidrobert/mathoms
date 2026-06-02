---
id: A23.l1
type: lane
title: "Data Lineage F0 — fechar 4 ADR Proposto + emenda ADR-146 (B1–B8)"
sprint: A23
plan: PLAN-data-lineage
status: shipped
priority: P0
branch_slug: a23-l1-data-lineage-f0-adr-gate
ship_date: 2026-06-03
adrs:
  - "[[ADR-278]]"
  - "[[ADR-279]]"
  - "[[ADR-280]]"
  - "[[ADR-281]]"
  - "[[ADR-146]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a23
  - status/shipped
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A23.l1 — Data Lineage F0 (gate de decisão)

> **Plano:** [[PLAN-data-lineage]] · Onda 0 · **gate absoluto** — nenhuma lane
> F1+ abre antes de B1–B8 travados.

## Objetivo

Fechar a família de 4 ADR `Proposto` ([[ADR-278]] A · [[ADR-279]] B · [[ADR-280]]
C · [[ADR-281]] D) + a emenda B1 em [[ADR-146]], resolvendo os 8 blockers de
corretude que as revisões `senior-cto` + `data-engineer` levantaram.

## Escopo

Para cada blocker, decisão textual + file:line + consequências no respectivo ADR:

- **B1** (ADR-146 emenda + ADR-278) — tie-break determinístico `(tier,
  kind-priority, alfabético por artifact_key)`, abandona `extracted_at`.
- **B2** (ADR-281) — `rule_ref` via dict literal eager + gate `check_lineage_refs`;
  ruling explícito [[ADR-111]] + entrada em `STATELESS_AUDIT.md §2`.
- **B3** (ADR-278) — K4 inclui `moeda`+`direction` com `hash_version`.
- **B4** (ADR-278) — **estratégia** de migração `natural_key` (2-passos
  nullable→obrigatório); a **auditoria de produtores E2 roda em F1**
  (`dl-f1-natural-key`), não no F0. O F0 decide o *como*, não executa o inventário.
- **B5** (ADR-278) — inventário de leitores de `valor`; gate de paridade decimal.
- **B6** (ADR-279) — retenção `artifact_lineage_edge`: `DELETE` cross-run, janela
  = último run por workspace (N=1).
- **B7** (ADR-278) — `SaldoContinuityValidator` filtra por `SourceRef.kind`.
- **B8** (ADR-279) — `member_hashes` ancorado ao `run_id`; sobreviventes pós-dedup.
- **[[ADR-280]]** — critério de corte Extract \| Transform fechado (gate F0 por
  critério, não por blocker numerado).

Plus detalhes de migration (CONCURRENTLY fora de transação Alembic; ordem
schema→strict do W6-T01).

## Critério de aceite (G0)

- 4 ADR `Proposto` mergeados em `main`; B1–B3, B5–B8 com resolução textual +
  file:line + consequências; **B4 com estratégia de migração decidida** (execução
  validada em F1); [[ADR-280]] (critério de corte) fechado.
- Emenda B1 em [[ADR-146]] + supersedure bidirecional [[ADR-045]]↔[[ADR-281]].
- Gates de doc verdes (`validate_frontmatter`, `check_doc_links`,
  `check_adr_anchors`, `check_doc_filename_id`, `build_doc_index --check`).
- **Docs-only** → mergeável sem CI verde; `pre-commit run --all-files` obrigatório.

## Owner sugerido

`senior-cto` (orquestra) + `data-engineer` (contrato/migração/retenção) —
ambos já revisaram o plano-fonte.
