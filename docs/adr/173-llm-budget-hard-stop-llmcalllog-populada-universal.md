---
id: ADR-173
type: adr
title: "LLM budget hard-stop + LLMCallLog populada universal"
status: Proposto
date: "2026-05-06"
relates_to: ["[[ADR-024]]", "[[ADR-025]]", "[[ADR-061]]", "[[ADR-122]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 173"]
tags:
  - type/adr
  - status/proposto
size_lines: 35
---

# ADR-173 — LLM budget hard-stop + LLMCallLog populada universal

**Status:** Proposto • **Data:** 2026-05-06 • **Relaciona** [ADR-024](#adr-024--litellm-como-proxy-universal), [ADR-025](#adr-025--byok-bring-your-own-key), [ADR-061](#adr-061--telemetria-privacy-first), [ADR-122](#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm). **Origem:** SR-006 + DE-013 (W3-T01).

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

**Implementação:** lane W3-T01. Vira `Decidido (W3-T01)` no merge.

**Referências:** [plan/PLATFORM_REVIEW/_README.md §W3-T01](plan/PLATFORM_REVIEW/_README.md), findings SR-006, DE-013.
