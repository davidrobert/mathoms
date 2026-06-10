---
id: A25.l7
type: lane
title: "Decisão do flip warn→strict do evidencia_path (requisito de done da A25)"
sprint: A25
plan: PLAN-data-lineage
status: planned
priority: P0
branch_slug: evidencia-strict-decision
adrs:
  - "[[ADR-279]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a25
  - status/planned
  - priority/p0
  - area/data-lineage
  - area/llm
---

# A25.l7 — `evidencia-strict-decision` (ÚLTIMA · requisito de done da sprint)

> **Plano:** [[PLAN-data-lineage]] · herdada de [[A24.l4]] (evidencia_path em modo
> `warn` desde 2026-06-10, telemetria ativa). Requisito de fechamento =
> **DECISÃO INFORMADA, não flip incondicional** (decisão owner 2026-06-10).

## Objetivo

Analisar a telemetria do `evidencia_path`
(`pipeline_stage_logs.output_summary`: `evidencia_failed`/`evidencia_verified` +
`failures_by_layer`) e decidir o flip `warn→strict`.

## Gate (cravado no kickoff)

- **Taxa de violação <5% sobre ≥20 gerações** → flipa: 1 linha
  (`evidencia_verification_mode: strict` em `config/prompts/parecer_planejador.yaml`),
  PR com a análise no corpo.
- **Taxa ≥5%** → NÃO flipa: ajustar regex/prompt (co-design `prompt-engineer`) e
  re-medir.
- **Amostra <20 gerações ao fim da sprint** → registrar decisão "carry-over A26 com
  gate idêntico" e a sprint fecha `done` mesmo assim — o flip não sequestra o
  fechamento.

## Acúmulo de amostra (desde o dia 1 da sprint)

Gerar parecer sobre goldens + dogfood na abertura e ao longo da sprint — a decisão
precisa de amostra; não deixar para o fim. Telemetria ativa desde 2026-06-10
([[A24.l4]] merge #580).

## Critério de aceite

- Decisão registrada (flip mergeado OU carry-over documentado) com a análise da
  telemetria no corpo do PR; nunca logar o VALOR (PII) — só camada + path.

## Owner

Agente da lane; co-design `prompt-engineer` se taxa ≥5%.
