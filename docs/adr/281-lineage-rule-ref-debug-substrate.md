---
id: ADR-281
type: adr
title: "rule_ref derivado de dict literal + lineage_diff (substrato de debug LLM)"
status: Decidido
phase: "A23 · F0"
date: "2026-06-02"
relates_to:
  - "[[ADR-143]]"
  - "[[ADR-111]]"
  - "[[ADR-116]]"
supersedes:
  - "[[ADR-045]]"
superseded_by: []
aliases: ["ADR 281", "rule_ref", "lineage_diff", "lineage debug substrate"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/data-lineage
  - area/llm
---

# ADR-281 — rule_ref derivado de dict literal + lineage_diff (substrato de debug LLM)

**Status:** Decidido (A23 · F0) • **Data:** 2026-06-02 • **Relaciona** [[ADR-143]], [[ADR-111]], [[ADR-116]] • **Supersede** [[ADR-045]].

> Camada D do plano [[PLAN-data-lineage]]. Gate F0 — **resolve B2**. Estende/supersede
> [[ADR-045]] (data lineage via tooltip — drill-down "para futuro"; este é esse futuro).
> Decisão fechada; lanes de implementação conformam.

**Contexto:** o lineage precisa ser legível por um LLM (agente de debug OU Claude Code no repo) para saltar de "número errado" → "função a corrigir". Exige bridge nó→código refactor-safe e diff de regressão determinístico. A [[ADR-045]] decidiu o tooltip de UI e adiou o drill-down; aqui materializamos o substrato.

**Decisão:**
- **Bridge nó→código:** **dict literal eager** `pipeline/domain/lineage_registry.py` (`{rule_id: "module:qualname", adr}`) — **não** decorator import-side-effect (banido por CLAUDE.md §Dependências; não cabe na exceção [[ADR-111]] (a), que é p/ constantes). Refactor-safe vem do gate `dev/check_lineage_refs.py` (resolve `module:qualname` por import real + ADR existe). Registrar em `STATELESS_AUDIT.md §2` (B2).
- **Renderer LLM:** trace linearizada (passos numerados raiz→folha, inputs como `#N`), teto ~1.5k tokens inline, anomaly-first ordering. Distinto do renderer humano (tooltip [[ADR-045]]).
- **`lineage_diff`** puro/stateless: só nós mudados + `first-divergent-leaf` + propagação anotada.
- **Tools:** `explain_number`/`expand_node`/`trace_source` (cap `max_expand_iterations:6`, whitelist de `field`). Superfície: core de domínio (Claude Code sobre goldens, dia 1); MCP read-only no console interno ([[ADR-116]], `workspace_id` obrigatório, zero mutação) — fase posterior.
- **Eval:** injeção determinística de bug; `localization_accuracy@node ≥ 85%`.

**Consequências:**
- ✅ LLM (Claude Code no repo OU agente de debug) salta de "número errado" → `rule_ref` → função exata. Bridge refactor-safe: o gate `check_lineage_refs` quebra se o `module:qualname` não resolve por import real, então rename sem atualizar o dict é pego no pre-commit.
- ✅ Supersede [[ADR-045]] (bidirecional: `superseded_by` no frontmatter de 045 já aponta para cá): o tooltip vira o **renderer humano**; o renderer LLM linearizado é a face de debug do mesmo grafo.
- ⚠️ **Rejeitado decorator `@lineage_rule`** (import-side-effect banido por CLAUDE.md §Dependências; não cabe na exceção [[ADR-111]] (a), que é p/ *constantes*, não registry populado por side-effect). Dict literal eager registrado em `STATELESS_AUDIT.md §2` como mapping de domínio imutável.
- ⚠️ **MCP prod do debug substrate + índice reverso por `rule_ref` deferidos** (YAGNI) até um agente fechar o loop "número errado → função" sobre goldens (F7). Não construir observability platform antes da pergunta de impacto real.
- ⚠️ Eval de injeção de bug (F7): `localization_accuracy@node ≥ 85%` (regressão >2% bloqueia merge), temp=0/seed/model pinados; o renderer LLM e o `lineage_diff` são `pipeline/domain/services/*` puros/stateless (não importam framework).
