---
id: ADR-280
type: adr
title: "Critério de corte Extract | Transform + check de pureza de extração"
status: Decidido
phase: "A23 · F0"
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
  - status/decidido
  - area/pipeline
  - area/data-lineage
---

# ADR-280 — Critério de corte Extract | Transform + check de pureza de extração

**Status:** Decidido (A23 · F0) • **Data:** 2026-06-02 • **Relaciona** [[ADR-242]], [[ADR-226]], [[ADR-246]], [[ADR-271]], [[ADR-081]].

> Camada C do plano [[PLAN-data-lineage]]. Gate F0 (por critério de pureza, não por blocker numerado). Decisão fechada; o de-leak executa em F2.

**Contexto:** para a fonte ser plugável (PDF/CSV ↔ feed) e o lineage referenciar uma fronteira estável, a extração deve fazer **só** extração. Hoje vaza transformação: `tipo_lancamento` (regex nos parsers), `numero_conta_norm` ([[ADR-226]]), hint de categoria ([[ADR-242]]). E1.5c (`consolidate_baseline`) é Transform mas vive no bloco de extração baseline.

**Decisão:**
- **Critério verificável:** extração não pode produzir campo cujo valor dependa de outro registro, de config de domínio do workspace, ou de decisão metodológica. Extração = função pura de *uma fonte → seus próprios registros*.
- Mover `tipo_lancamento` → Transform (auditar consumidores antes — pode ser load-bearing). `numero_conta_norm` → camada canônica/Transform.
- Hint de categoria: reclassificar como **sinal de fonte** (`{value, origin:"llm_extract", confidence}`) — não deletar (evita 2ª passada LLM); E4 decide. Já perto da [[ADR-242]] §D4.
- Rotular `consolidate_baseline` (E1.5c) como Transform.
- Enforcement: `dev/check_extract_no_domain_imports.py` (extração ∌ `category_template`/`*_dedup`/`ConfigStore`) + `validate_full_order` estendido.

**Consequências:**
- ✅ Extração vira função pura de fonte → registros; o lineage ([[ADR-279]]) referencia uma fronteira estável (refs apontam para o stage Transform onde a regra mora, não para o parser).
- ✅ `check_extract_no_domain_imports` impede *novos* vazamentos por construção (AST de imports, irmão de `check_pipeline_boundaries`).
- ⚠️ **F2 é a fase mais arriscada** (toca goldens E2/E3/E4 + dedup [[ADR-246]]/[[ADR-271]]). `tipo_lancamento` pode ser load-bearing → `dl-f2-discovery` mapeia consumidores (blast radius numérico) **antes** de mover; de-leak fatiado (slice1 = só fronteiras do skeleton; residual paraleliza); rebaseline isolado com manifesto justificado (G-c).
- ⚠️ Hint de categoria **não é deletado** (recomputar no E4 = 2ª passada LLM): vira sinal de fonte (`origin=llm_extract`, `confidence`), E4 decide — alinhado à [[ADR-242]] §D4.
- ⚠️ `consolidate_baseline` (E1.5c) é rotulado Transform (lê cross-IRPF, dedup) — já é stage separado; o check passa a permitir seus imports de domínio, e proíbe nos stages de extração pura.
