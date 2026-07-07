---
id: ADR-173
type: adr
title: "LLM budget hard-stop + LLMCallLog populada universal"
status: Decidido
phase: W3-T01
date: "2026-05-06"
relates_to: ["[[ADR-024]]", "[[ADR-025]]", "[[ADR-061]]", "[[ADR-122]]"]
supersedes: []
superseded_by: []
amended_at: ["2026-07-07"]
aliases: ["ADR 173"]
tags:
  - area/llm
  - area/money
  - area/multitenancy
  - status/decidido
  - type/adr
size_lines: 35
---

# ADR-173 — LLM budget hard-stop + LLMCallLog populada universal

> **Emendada em 2026-07-07** — clamp `MAX_SETTABLE_BUDGET_USD` do editor
> de budget calibrado para US$ 300 (ver §Emenda ao final).

**Status:** Decidido (W3-T01) • **Data:** 2026-05-06 • **Relaciona** [ADR-024](#adr-024--litellm-como-proxy-universal), [ADR-025](#adr-025--byok-bring-your-own-key), [ADR-061](#adr-061--telemetria-privacy-first), [ADR-122](#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm). **Origem:** SR-006 + DE-013 (W3-T01).

**Contexto:** Mathoms cobre custo LLM via BYOK (ADR-025) ou pool gerenciado. Hoje **não há cap** — workspace adversarial pode disparar 10k chamadas custando $1k+ antes de qualquer alerta. `LLMCallLog` existe no schema mas é populado de forma incompleta (alguns stages chamam, outros não). ADR-024 declarou LiteLLM como proxy mas não enforce budget; ADR-061 garante privacy mas não custo.

**Alternativas avaliadas:**

1. **Status quo (sem cap, log inconsistente)** — risco financeiro inaceitável em produção multi-tenant. Rejeitada.
2. **Cap mensal soft-warn only** — não previne abuso intencional. Rejeitada.
3. **Hook universal em `litellm_client.py` + cap hard-stop com cache 60s (escolhida)** — todo call passa pelo gateway; pre-call check Redis-cached é barato.

**Decisão:** Adotar (3).

- **Hook universal:** `litellm_client.py` envolve toda chamada em `LLMService.call(prompt, model, workspace_id, prompt_version)`. Antes do call, query budget; depois do call, persist `LLMCallLog` com tokens + custo USD.
- **Budget storage:** workspace tem `monthly_llm_budget_usd: Decimal | None`. NULL = unlimited (default em dev/staging).
- **Thresholds:**
  - **80%:** soft-warn — Notification + métrica `mathoms.llm.budget_warn`.
  - **110%:** hard-stop — pre-call check rejeita com `LLMBudgetExceededError`. UI mostra mensagem "limite mensal atingido — contate suporte".
- **Cache 60s Redis** para `SUM(cost_usd)` per workspace — query SQL evitada na maioria das chamadas.
- **PROMPT_VERSION** declarado em todo prompt LLM (gate W2-T05) é persistido com cada `LLMCallLog` para drift tracking.

**Consequências:**

- ✅ Cap financeiro enforce — abuso ou bug em loop não vira incidente $$$.
- ✅ Auditoria completa de custo por workspace (LGPD: dados próprios do usuário).
- ✅ Drift de prompt detectável via correlação `(prompt_version, output_quality_metrics)` em CI nightly.
- ⚠️ Cache 60s pode permitir burst até 60s de chamadas pós-110%. Aceito; usuário malicioso ainda paga + Notification dispara.
- ❌ Não cobre budget per-stage ou per-tier — first iteration é workspace-scoped mensal.

**Implementação:** lane W3-T01 (2026-07-02) — hooks via `LLMConfig.call_hooks`
(protocol em `pipeline/llm/call_hooks.py`; `LLMBudgetService` no backend
injetado em `_setup_run_context` + `ParecerOrchestratorConfig.llm_hooks`);
`monthly_llm_budget_usd` nullable (NULL = sem cap) na migration
`adr173budgetnull`.

**Referências:** [plan/PLATFORM_REVIEW/_README.md §W3-T01](../plan/PLATFORM_REVIEW/_README.md), findings SR-006, DE-013.

## Emenda — clamp do editor de budget calibrado (2026-07-07)

A30.l1 (PR #815) criou o editor de `monthly_llm_budget_usd` no console
interno com clamp anti-typo `MAX_SETTABLE_BUDGET_USD` (`backend/app/schemas/
admin.py`), inicialmente US$ 1.000 (chute). Lane [[A31.l2]] calibra para
**US$ 300/mês** com racional do `financial-planner` (2026-07-07):

- ~50× o P99 de uso real observado (US$ 5,57/mês no workspace mais pesado,
  32 calls) — nunca atrapalha operação legítima, multi-declarante incluso.
- Corta o blast radius de typo em 70% vs US$ 1.000; ordem de grandeza acima
  da faixa de COGS que um premium R$ 50-150 comporta (US$ 2-8/ws/mês a
  20-30% da receita).
- O clamp NÃO é o número de margem (esse é o default US$ 5 + hard-stop 110%
  desta ADR); é a barreira de sanidade acima da faixa de negócio.

**Gatilhos de recalibração:** (a) pricing definido → clamp vira função do
tier top (ex.: 10× o budget do plano mais caro), não constante; (b) P99
real > ~US$ 30/mês; (c) troca de modelo com pricing materialmente diferente.
