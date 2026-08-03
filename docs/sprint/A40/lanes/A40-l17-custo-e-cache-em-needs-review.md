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

> Onda 0 do §Frente 4 de [[PLAN-report-trust]]. Cortável se a onda apertar.

## Problema

No run `2ded7aab` o `output_summary` do stage reportou
`tokens {in: 0, out: 0}, cost_usd 0.0`, enquanto o `llm_call_log` registrou
**76.133 in / 17.000 out / US$ 0,4834**. Causa: `_needs_review()`
([`parecer_orchestrator.py:241`](../../../../backend/app/services/parecer_orchestrator.py))
monta o resultado de `_base_result` (tokens default 0) e **nunca** chama
`_extract_last_call_metrics(llm)`, que só existe no caminho de sucesso.

Todo `needs_review` esconde o gasto real do hard-stop de budget ([[ADR-173]]).

Segundo defeito no mesmo caminho: **`needs_review` não escreve cache** — só o
caminho de sucesso alcança `_write_cache`. Cada falha re-paga a geração inteira.

## Decisão

1. `_needs_review()` lê `_extract_last_call_metrics(llm)` quando houve chamada
   LLM, com paridade de campos ao `_success_result`.
2. Invariante: **nenhum caminho de retorno do parecer reporta custo 0 quando
   houve chamada LLM.**
3. Escrever cache no caminho `needs_review`, chaveado pela mesma composição
   (inclui `ev{N}`, então o bump da [[A40.l16]] invalida o que houver).

## Critério de aceite

- Teste: fake de LLM com métricas conhecidas + resultado `needs_review` ⇒
  `status["cost_usd"]` e `status["tokens"]` batem com o fake.
- Teste: soma de `cost_usd` dos `output_summary` de um run == soma do
  `llm_call_log` para o mesmo `pipeline_run_id`.
- Segundo run com mesmo `e5_hash` após um `needs_review` ⇒ `cache_hit: True`,
  zero chamada LLM nova.
- **Não é KR** (é asserção de corretude); vira health metric do painel FinOps.
