---
id: A33.l7
type: lane
title: "OTLP mathoms.llm.* por {prompt_name, prompt_version} + parecer.riscos_truncados (W3)"
sprint: A33
plan: PLAN-llm-prompts-hardening
status: planned
priority: P2
branch_slug: a33-l7-otlp-telemetria-llm
adrs: ["[[ADR-110]]"]
depends_on: ["[[A33.l3]]"]
parallel_with: ["[[A33.l8]]"]
tags:
  - type/lane
  - sprint/a33
  - status/planned
  - priority/p2
  - area/observability
---

# A33.l7 — `otlp-telemetria-llm` (W3 do [[PLAN-llm-prompts-hardening]])

## Problema

Com `confidence`/`prompt_version` persistidos em SQL ([[A33.l3]]), falta
a camada OTLP ([[ADR-110]], opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT`)
para observar drift entre versões sem query manual:
`confidence_p50/p95`, `needs_review_rate`, `cache_hit_rate` e
`parecer.riscos_truncados` (métrica que calibra o cap ≤12 riscos do
parecer — decisão "aprovado como está, telemetria mede" do plano).

## Escopo

1. Métricas `mathoms.llm.*` com labels compostos
   `{prompt_name, prompt_version}` (decisão 2 da revisão do plano —
   nunca slug embutido na string de versão).
2. `parecer.riscos_truncados` no ponto de truncamento do parecer.
3. Emissão a partir do choke point existente
   (`pipeline/llm/litellm_client.py` via protocol — pipeline não importa
   backend; injection segue o padrão dos hooks da [[ADR-307]]).
4. Sem estado mutável em módulo ([[ADR-111]]) — counters via SDK OTLP.

## Critérios de aceite

1. Com endpoint OTLP configurado, métricas aparecem com os 2 labels;
   sem endpoint, zero overhead (opt-in preservado).
2. Teste unitário com exporter in-memory cobrindo as 4 métricas.
3. PR mergeado em `main` (squash) com CI verde.
