---
id: A40.l17
type: lane
title: "Custo e cache no caminho needs_review do parecer: US$ 0,48 reportados como zero"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l17-custo-e-cache-em-needs-review
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/backend
  - area/llm
---

# A40.l17 — `custo-e-cache-em-needs-review`

> Onda 0 da A40 (§Frente 4 de [[PLAN-report-trust]]). Cortável se a onda apertar.
> **Consumidor futuro declarado:** quando a [[A40.l20]] passar a persistir o
> desfecho gerado-e-retido, `PlannerReview.cost_usd_cents` deriva do detail — sem
> esta lane, o zero contamina o registro durável. Emenda canônica: [[ADR-199]]
> §Emenda 2026-08-03.

## Problema

No run `2ded7aab` o `output_summary` do stage reportou
`tokens {in: 0, out: 0}, cost_usd 0.0`, enquanto o `llm_call_log` registrou
**76.133 in / 17.000 out / US$ 0,4834**. Causa: `_needs_review()`
([`parecer_orchestrator.py:241`](../../../../backend/app/services/parecer_orchestrator.py))
monta o resultado de `_base_result` (tokens default 0) e **nunca** chama
`_extract_last_call_metrics(llm)`, que só existe no caminho de sucesso.

> **Correção do dano declarado (co-design 2026-08-03).** A versão original desta
> lane afirmava *"todo `needs_review` esconde o gasto real do hard-stop de budget
> ([[ADR-173]])"* — **falso**: `_month_spend_from_db`
> (`llm_budget_service.py`) soma `LLMCallLog.cost_usd` e nunca leu
> `output_summary`. O dano real é (a) leitura humana/agente do stage log cega, e
> (b) contaminação futura de `PlannerReview.cost_usd_cents` via [[A40.l20]]. É
> defeito de telemetria, não de segurança de budget.

Segundo defeito no mesmo caminho: **`needs_review` não escreve cache** — só o
caminho de sucesso alcança `_write_cache`.

## Decisão (revisada em co-design, 2026-08-03)

1. ✅ `_needs_review()` recebe as métricas da chamada com paridade de campos ao
   `_success_result` — via VO frozen `LLMCallMetrics` extraído **uma vez** no
   orchestrator (ADR-089/097: builder não duck-typa o `LLMService`).
2. ✅ Invariante **reescrito** — a forma original ("nenhum caminho reporta custo 0
   quando houve chamada") era auto-referente (o observável de "houve chamada" é a
   mesma fonte do custo) e vacuamente verdadeira na classe mais cara: falha
   pós-cobrança não deixa entry em `summary.calls` **nem** em `llm_call_log`
   (`LLMService.call` só registra após `create()` retornar). Substituído por
   **polaridade pinada nos dois sentidos + `cost_known`**: zero legítimo continua
   zero (cache hit, `llm is None`); ausência de registro após tentativa sai
   `cost_known=False` (desconhecido ≠ grátis; paridade com a coluna homônima de
   `LLMCallLog`).
3. ❌ **REVOGADA — não cachear `needs_review`.** Dois motivos independentes
   ([[ADR-199]] §Emenda E1): o cache serializa só o `ParecerPlanejadorOutput` e um
   hit devolveria o placeholder como `status="Gerado"` (publicável); e sob temp
   0.1 **a re-geração é o retry** — cachear a amostra rejeitada por 7 dias, sem
   `delete` no `LLMCacheBackend`, converte sorteio ruim em bloqueio de uma semana.
   Re-pagar é o preço correto. No lugar, o invariante oposto virou **gate**:
   `tests/test_parecer_cache_policy.py` pina "caminho de rejeição não cacheia",
   com prova de mutação. Se cooldown virar necessidade, é lane própria (TTL ≤15
   min, zero payload, flush primeiro).
4. ✅ (achado do co-design) `_try_cache` era a única leitura **fail-closed** ao
   lado de um write fail-open ([[ADR-144]]) — entrada envenenada derrubava o
   stage em todo retry até o TTL de 7d expirar, sem via de flush. Corrigida para
   fail-open simétrico.

## Critério de aceite (cumprido)

- ✅ Fake com métricas conhecidas + `needs_review` pós-chamada (sigilo) ⇒
  `cost_usd`/`tokens_*` batem com o fake, em paridade com o sucesso
  (`tests/test_parecer_custo_em_needs_review.py`).
- ✅ Polaridade pinada: cache hit e `llm is None` continuam `0.0` com
  `cost_known=True`; falha sem registro sai `cost_known=False`.
- ✅ Gate de política de cache nos caminhos de rejeição + contra-prova de que o
  sucesso escreve (senão o gate é vacuamente verde), com **prova de mutação nos
  dois sentidos** (reverter fail-open ⇒ 2 testes caem; simular a Decisão 3
  original ⇒ gate dispara).
- ✅ `cost_known` exposto no detail do stage (`_needs_review_return` e
  `_success_return`).
- ❌ **Removido** — "soma de `cost_usd` dos `output_summary` == soma do
  `llm_call_log` por run": inalcançável como escrito (3 stages LLM não emitem
  custo no detail; `_record_stage_exception` sobrescreve o detail; retry/resume
  gera N stage logs). Uma paridade **escopada** a
  `(pipeline_run_id, 'review_finances_holistic')` ±1 cent é possível, mas prova
  consistência interna, nunca verdade contábil (reasks internos faturados não
  entram em nenhuma das duas fontes) — registrada como follow-up, não critério.
- ❌ **Removido** — "vira health metric do painel FinOps": pressupõe view por-run
  que não existe.

## Residual (fora desta lane, com dono)

- **O dinheiro invisível está na falha sem registro**, não nos caminhos que esta
  lane corrigiu: reask storm / timeout pós-cobrança não deixam rastro em
  `summary.calls` nem em `llm_call_log` (append/record só após `create()`
  retornar). Fix é no choke-point (`pipeline/llm/litellm_client.py`) com emenda à
  [[ADR-173]] — lane própria, gatilho `prompt-engineer`.
- **`persona_hash` fora da cache key** (achado `senior-cto`, pior que o defeito
  desta lane): editar a persona **não invalida** o cache — até 7 dias servindo
  parecer da persona antiga. Uma linha no composite, mesma família da emenda
  2026-06-12 da [[ADR-199]]. Também para lane própria; não embarcou aqui para não
  misturar invalidação de cache com contabilidade.
- **`config.tier` fora da key**: hit cross-tier faz `tier_at_generation` do
  envelope divergir do `output.metadata` — mesmo destino.
