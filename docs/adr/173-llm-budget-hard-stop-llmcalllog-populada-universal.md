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
amended_at: ["2026-07-07", "2026-07-15"]
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
>
> **Emendada em 2026-07-15 (DE-01)** — `llm_call_log` consagrada como **SSOT**
> de FinOps de LLM; `pipeline_run_costs` deprecada em 3 fases (0 auditoria → 1
> parar de escrever → soak ≥1 mês → 2 drop + snapshot). Budget hard-stop
> **inalterado**. Ver §Emenda 2026-07-15 ao final.

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

**Referências:** [archive/PLATFORM_REVIEW_PLAN-2026-07-08.md §W3-T01](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md), findings SR-006, DE-013.

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

## Emenda 2026-07-15 (DE-01) — `llm_call_log` como SSOT de FinOps; deprecar `pipeline_run_costs`

**Contexto.** Co-design `data-engineer` (2026-07-15, item DE-01 do dogfood).
Levantamento empírico do código:

- `pipeline_run_costs` tem **1 writer** (`planner_review_persistence.py::_build_cost_row`,
  stage sempre `review_finances_holistic`) e **zero leitor de produção** — os
  endpoints ops de custo (`admin/metrics.py`) já leem **exclusivamente**
  `llm_call_log`. O cutover funcional já ocorreu.
- O custo do parecer **já é gravado em `llm_call_log`** pelo hook universal desta
  ADR (mesmo `run_id`, mesmo stage). `llm_call_log` é **superset estrito** de
  `pipeline_run_costs` (cobre o parecer + os outros 7 stages). Nenhum valor de
  custo é exclusivo, **exceto** os runs de parecer da janela **2026-05-13
  (criação da tabela) → 2026-07-02 (chegada do hook universal)**, que têm custo
  só em `pipeline_run_costs`.

**Decisão.** `llm_call_log` é o **SSOT** de custo de LLM. `pipeline_run_costs` é
deprecada e removida em **3 fases**, com o budget hard-stop desta ADR
**inalterado** (`_month_spend_from_db` já soma `llm_call_log`, nunca tocou
`pipeline_run_costs`):

- **Fase 0 — auditoria de paridade (read-only, gate):** `dev/de01_finops_parity_audit.py`
  reconcilia, por `(pipeline_run_id, stage)`, `pipeline_run_costs.cost_usd_cents`
  vs `ROUND(SUM(llm_call_log.cost_usd)*100)`; aceite = mismatch 0 (±1 cent) +
  contagem das rows órfãs pré-hook reportada. Roda em staging/prod (não no worktree).
- **Fase 1 — parar de escrever (code-only, reversível):** remove o writer de
  `planner_review_persistence.py`. Model + tabela + allowlist LGPD **ficam**.
  Sem migration; revert de código reverte 100%. **Esta emenda entrega a Fase 1.**
  Inicia o soak.
- **Fase 2 — drop (pós-soak ≥1 mês, owner/ops-gated):** migration **nova**
  (não downgrade da `e3d4e5f6a7b8`, que também cria `planner_review_metadata`
  vivo) no head único; drop dos índices + `drop_table`; **atômico** no mesmo PR:
  deletar o model + entradas em `models/__init__.py` + **remover `"pipeline_run_costs"`
  de `EXPORT_EXCLUDED_TABLES`** (`lgpd_export_service.py`) + regenerar
  `DB_SCHEMA_REFERENCE.md`. **Snapshot cold off-DB obrigatório** antes do drop
  (a janela pré-hook tem custo exclusivo).

**Correção de premissa (LGPD).** O export LGPD **não lê** `pipeline_run_costs` —
ambas as tabelas estão em `EXPORT_EXCLUDED_TABLES` (telemetria técnica, fora da
portabilidade Art.18). **Não há read-side a repontar**; o que o titular recebe
**não muda**. A única ação LGPD é remover a chave do allowlist, **acoplada e
atômica** com a deleção do model (senão `test_lgpd_export_coverage.py` fica
vermelho — valida `EXPORT_EXCLUDED_TABLES ⊆ Base.metadata.tables`).
