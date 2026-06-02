---
id: ADR-278
type: adr
title: "SourceAdapter + SourceRef + data_source + contrato canônico E2 v3"
status: Proposto
phase: "A23"
date: "2026-06-02"
relates_to:
  - "[[ADR-255]]"
  - "[[ADR-212]]"
  - "[[ADR-090]]"
  - "[[ADR-146]]"
  - "[[ADR-226]]"
  - "[[ADR-241]]"
supersedes: []
superseded_by: []
aliases: ["ADR 278", "SourceAdapter", "SourceRef"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/data-lineage
  - area/persistence
---

# ADR-278 — SourceAdapter + SourceRef + data_source + contrato canônico E2 v3

**Status:** Proposto (A23) • **Data:** 2026-06-02 • **Relaciona** [[ADR-255]], [[ADR-212]], [[ADR-090]], [[ADR-146]], [[ADR-226]], [[ADR-241]].

> Camada A do plano [[PLAN-data-lineage]]. Gate F0 — **resolve B1, B3, B4, B5, B7**.
> Stub `Proposto`; a decisão fecha no F0 antes de qualquer lane F1.

**Contexto:** o pipeline já é hexagonal na fonte (`N adapters → artefato E2 → downstream agnóstico`), mas o contrato não está nomeado como porta nem isolado de extração. Integrar Open Finance / agregador exige uma porta `SourceAdapter` e uma referência de fonte (`SourceRef`) que generalize o `document_id` — folha estável do lineage.

**Decisão (a fechar no F0):**
- `SourceAdapter` Protocol + `SourceRef` discriminated union (`document` | `feed`) em `pipeline/domain/ports/source.py`.
- Contrato canônico = artefato E2 endurecido (`e2_extract.schema.json` v3): `natural_key` (K4) obrigatório com `hash_version`, `amount` decimal ([[ADR-090]]), `source_ref`, `direction`.
- Tabela `data_source` + `pipeline_artifacts.data_source_id` (nullable FK `ON DELETE SET NULL`); `document_id` permanece.
- **B1:** tie-break determinístico `(tier, kind-priority, alfabético por artifact_key)` — não `extracted_at` (ver emenda [[ADR-146]]).
- **B3:** K4 inclui `moeda` + `direction` (via `hash_version`, retro-compat).
- **B4:** auditar produtores E2; `natural_key` em migração 2-passos nullable→obrigatório onde produtor não emite K4.
- **B5:** inventário de leitores de `valor`; gate `Decimal(amount)==Decimal(str(valor))` na janela dupla.
- **B7:** `SaldoContinuityValidator` filtra por `SourceRef.kind` (só série `document` vira saldo-âncora).

**Consequências:** (a preencher no F0 — migração online, `CREATE INDEX CONCURRENTLY` fora de transação Alembic, backfill `kind='document'`).
