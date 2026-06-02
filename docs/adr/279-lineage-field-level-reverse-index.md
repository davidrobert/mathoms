---
id: ADR-279
type: adr
title: "Lineage field-level inline (_lineage) + índice reverso artifact_lineage_edge"
status: Proposto
phase: "A23"
date: "2026-06-02"
relates_to:
  - "[[ADR-216]]"
  - "[[ADR-090]]"
  - "[[ADR-111]]"
  - "[[ADR-241]]"
  - "[[ADR-271]]"
  - "[[ADR-255]]"
supersedes: []
superseded_by: []
aliases: ["ADR 279", "lineage field-level", "artifact_lineage_edge"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/data-lineage
---

# ADR-279 — Lineage field-level inline (_lineage) + índice reverso artifact_lineage_edge

**Status:** Proposto (A23) • **Data:** 2026-06-02 • **Relaciona** [[ADR-216]], [[ADR-090]], [[ADR-111]], [[ADR-241]], [[ADR-271]], [[ADR-255]].

> Camada B do plano [[PLAN-data-lineage]]. Gate F0 — **resolve B6, B8**.
> Stub `Proposto`; decisão fecha no F0.

**Contexto:** validar/debugar um número exige hoje arqueologia stage-a-stage. Queremos lineage declarativo field-level inline no `content_json` (cabe via `additionalProperties:true`, generaliza `real_estate.componentes_calculo` da [[ADR-216]] D9), forward via `LineageResolver` stateless, e reverso via tabela derivada. **Rejeitado `TracedValue`** (reescreveria a aritmética float, arrisca [[ADR-090]]/[[ADR-111]]).

**Decisão (a fechar no F0):**
- Bloco `_lineage` inline: `{value (Decimal string), label, transform, rule_ref, edge_type, signals, member_hashes, inputs}`. Invariantes: zero timestamp/UUID, `inputs` sorted, `value` espelhado (gate em cents int), folha = `data_source_id`/`SourceRef[]`.
- `LineageResolver` read-only, stateless ([[ADR-111]]) — nós `dangling`/`no_lineage`, nunca exceção.
- Tabela `artifact_lineage_edge` derivada/rebuildável via stage terminal `materialize_lineage`; `rule_ref` como coluna TEXT; índices `(workspace_id, rule_ref)` e `(workspace_id, source_document_id)`.
- **B6:** `materialize_lineage` faz `DELETE` cross-run (retenção — [[ADR-241]] matou o GC implícito).
- **B8:** `member_hashes` = K4 sobreviventes pós-dedup, resolver ancora lookup ao `run_id` do agregado (não most-recent workspace-scoped). Gate `check_lineage_sum`.
- `_lineage` declarado em `e5_analysis.schema.json` antes/junto do flip→strict (PLATFORM_REVIEW W6-T01).

**Consequências:** (a preencher no F0 — rebaseline de goldens E5 esperado; determinismo do payload garantido por gates).
