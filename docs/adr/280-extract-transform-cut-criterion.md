---
id: ADR-280
type: adr
title: "Critério de corte Extract | Transform + check de pureza de extração"
status: Proposto
phase: "A23"
date: "2026-06-02"
relates_to:
  - "[[ADR-242]]"
  - "[[ADR-226]]"
  - "[[ADR-246]]"
  - "[[ADR-271]]"
  - "[[ADR-081]]"
supersedes: []
superseded_by: []
aliases: ["ADR 280", "Extract Transform cut"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/data-lineage
---

# ADR-280 — Critério de corte Extract | Transform + check de pureza de extração

**Status:** Proposto (A23) • **Data:** 2026-06-02 • **Relaciona** [[ADR-242]], [[ADR-226]], [[ADR-246]], [[ADR-271]], [[ADR-081]].

> Camada C do plano [[PLAN-data-lineage]]. Gate F0. Stub `Proposto`; decisão fecha no F0.

**Contexto:** para a fonte ser plugável (PDF/CSV ↔ feed) e o lineage referenciar uma fronteira estável, a extração deve fazer **só** extração. Hoje vaza transformação: `tipo_lancamento` (regex nos parsers), `numero_conta_norm` ([[ADR-226]]), hint de categoria ([[ADR-242]]). E1.5c (`consolidate_baseline`) é Transform mas vive no bloco de extração baseline.

**Decisão (a fechar no F0):**
- **Critério verificável:** extração não pode produzir campo cujo valor dependa de outro registro, de config de domínio do workspace, ou de decisão metodológica. Extração = função pura de *uma fonte → seus próprios registros*.
- Mover `tipo_lancamento` → Transform (auditar consumidores antes — pode ser load-bearing). `numero_conta_norm` → camada canônica/Transform.
- Hint de categoria: reclassificar como **sinal de fonte** (`{value, origin:"llm_extract", confidence}`) — não deletar (evita 2ª passada LLM); E4 decide. Já perto da [[ADR-242]] §D4.
- Rotular `consolidate_baseline` (E1.5c) como Transform.
- Enforcement: `dev/check_extract_no_domain_imports.py` (extração ∌ `category_template`/`*_dedup`/`ConfigStore`) + `validate_full_order` estendido.

**Consequências:** (a preencher — F2 é a fase mais arriscada: rebaseline E2/E3 isolado em commit separado; discovery dimensionado como gate de entrada).
