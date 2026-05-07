---
id: ADR-092
type: adr
title: "Renomear scripts para nomes descritivos de domínio"
status: Proposto
phase: "execução na Fase 9 pós-Caminho B dos stages"
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 092"]
tags:
  - area/pipeline
  - status/proposto
  - type/adr
size_lines: 42
---

# ADR-092 — Renomear scripts para nomes descritivos de domínio

**Status:** Proposto (execução na Fase 9 pós-Caminho B dos stages) • **Data:** 2026-04-19 • **Plano:** Fase 9.4

**Contexto:** Scripts em `scripts/` usam o padrão `eN_nome.py` (ex: `e3_reconcile.py`,
`e5_analyze.py`). O número implica posição na fila — responsabilidade do
orquestrador, não do arquivo. Conflita com o rename de stage identifiers
(ADR-093) e acopla o nome do arquivo à ordem de execução, dificultando
refactor.

**Decisão:** Renomear os scripts para nomes descritivos de domínio usando
`git mv` (preserva histórico):

| Antes | Depois |
|---|---|
| `scripts/e0_audit.py` | `scripts/document_auditor.py` |
| `scripts/e0_route.py` | `scripts/document_router.py` |
| `scripts/e0_unlock.py` | `scripts/document_unlocker.py` |
| `scripts/e15_consolidate.py` | `scripts/baseline_consolidator.py` |
| `scripts/e2_extract.py` | `scripts/transaction_extractor.py` |
| `scripts/e3_reconcile.py` | `scripts/transaction_reconciler.py` |
| `scripts/e4_categorize.py` | `scripts/transaction_categorizer.py` |
| `scripts/e5_analyze.py` | `scripts/financial_analyzer.py` |
| `scripts/e5n_narrativas.py` | `scripts/narrative_generator.py` |
| `scripts/e6_render.py` | `scripts/report_renderer.py` |
| `scripts/e7_review.py` | `scripts/quality_reviewer.py` |

Wrappers em `pipeline/stages/` também são renomeados (ver ADR-093).

**Pré-requisito:** Fases 5-8 completas (stages em Caminho B). Renomear antes
mantém o sistema consistente, rename antecipado cria estado misto perigoso.

**Consequências:**
- ✅ Nomes descrevem a operação de domínio, não a posição na fila.
- ✅ `git mv` preserva histórico — blame funciona.
- ⚠️ Imports em todo o codebase precisam ser atualizados (guardrail: grep
  survivors no CI da Fase 9.5).
- ❌ Scripts de automação externos (cron, CI externo) que invocam
  `python scripts/eN_*.py` quebram — 1 release de alias em `e_reset.py`
  mitiga parcialmente.
