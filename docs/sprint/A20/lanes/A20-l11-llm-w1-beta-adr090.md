---
id: A20.l11
type: lane
title: "LLM Hardening — W1β ADR-090 cadeia e15_baseline (float → Decimal)"
sprint: A20
plan: PLAN-llm-prompts-hardening
status: planned
priority: P0
branch_slug: a20-l11-llm-w1-beta-adr090
parallel_with:
  - "[[A20.l12]]"
adrs:
  - "[[ADR-259]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
tags:
  - type/lane
  - sprint/a20
  - status/planned
  - priority/p0
  - area/llm
  - area/money
  - breaking/schema
---

# A20.L11 — W1β ADR-090 cadeia `e15_baseline` (2 PRs)

> **Onda 1β do plano [[PLAN-llm-prompts-hardening]].** Isolada de W1α para não acoplar gate Beta com risco de cadeia `Decimal`. **Risco alto na cadeia downstream** confirmado pelo `data-engineer`: consumers atuais aritmetizam `float`.

## Objetivo

Corrigir violação [[ADR-090]] em `pipeline/llm/schemas/e15_baseline.py:20,31-33` (`value_brl: float`, `total_assets_brl: float`, etc.) + propagar para schema JSON + consumer chain (`extract_baseline → consolidate_baseline → e4_categorizer`).

Drift de 0,01 importa em cenários do produto (revisão `financial-planner`):
- **Progresso IF Perini** — `progresso_if_pct` em patrimônio R$ 3M.
- **Desvio AUVP por classe** — KR de aporte mensal escolhe classe defasada borderline.
- **Auditoria fiscal / partilha / inventário** — cliente alta renda PJ levanta o relatório em sucessão.

## Critério de aceite (gate binário falsifiável)

- `grep -rn "value_brl: float\|total_assets_brl: float" pipeline/llm/schemas/` retorna 0.
- Consumer chain `extract_baseline → consolidate_baseline → e4_categorizer` passa em testes E2E com `Decimal`/string decimal sem perda de precisão.
- `config/schemas/baseline_patrimonial.schema.json` com pattern string decimal `^-?\d+(\.\d{1,2})?$` + `additionalProperties: false`.
- 0 rows em `pipeline_artifacts` (stages `E1.5`/`E1.5a`/`E1.5c`) com payload number-typed (após backfill).
- `SCHEMA_BY_STAGE` em `backend/app/services/db_artifact_store.py` cobre `E1.5` e `E1.5a` (gap atual).
- `pytest tests -q -k "baseline or e15"` verde.

## Sub-tarefas (2 PRs sequenciais)

### W1β-T01 — Audit downstream + serializer canônico (~1.5d)

Auditar consumers de `BaselinePatrimonialOutput`:

- `pipeline/stages/extract_baseline.py:43-58` — consome `item.value_brl`, `output.total_assets_brl`, `output.net_worth_brl`.
- `pipeline/llm/validators.py` — aritmética `sum(i.value_brl ...)`, `abs(computed - output.total_assets_brl)`.
- `pipeline/domain/services/e4_categorizer_adapter.py:194` — consome baseline via E5.
- `consolidate_baseline` (E1.5c) — pré-baseline.

Entregas:

- Helper `_baseline_to_legacy_dict(output) → dict` em `extract_baseline.py` que serializa `Decimal → str` (não `float`).
- Migrar `validators.py` para aritmética `Decimal`.
- Schema JSON: `config/schemas/baseline_patrimonial.schema.json:55-69,131` → `"type": "string", "pattern": "^-?\\d+(\\.\\d{1,2})?$"` + `additionalProperties: false` + `payload_version` no envelope.
- Mapping `SCHEMA_BY_STAGE`: adicionar `E1.5` e `E1.5a`.

### W1β-T02 — Schema + prompt + fixture atomic (~1.5d)

- Schema `e15_baseline.py`: `value_brl`/`total_assets_brl`/`total_liabilities_brl`/`net_worth_brl` → `Decimal` com `_coerce_decimal` validator (padrão `e16_irpf_full.py:23`).
- Prompt `e15_baseline.py`: substituir `"150000.00, não R$ 150.000,00"` por string decimal explícita. Adicionar regra de mask CPF (espelhar `apolice.py` §10).
- Bump `PROMPT_VERSION` (`"1.0.0"` → `"1.1.0"`).
- Atualizar fixture `tests/fixtures/llm_golden/e15_baseline_output.json` para strings decimais.
- Migration de payloads históricos: `pipeline_artifacts` stage `E1.5`/`E1.5a`/`E1.5c` → re-validar; falhas marcadas para re-extração ([[ADR-261]] Tier 3).
- **PR atomic**: schema + prompt + validators + serializer + fixture + golden test prova consumer chain.

## Coordenação

Paralelo a [[A20.l12]] (W2 — versioning + goldens) — não competem por arquivos. Sequenciar com [[A20.l11]] sem dependência forte; [[A20.l12]] T01 (semver puro de e15_baseline) precisa esperar W1β T02 estabilizar.

**Depende de**: nada. Pode iniciar imediatamente após A20 abrir.

## Detalhe operacional

Plano canônico: [[PLAN-llm-prompts-hardening]] §W1β. ADRs canônicas: [[ADR-259]] (boundary LLM unificado) + [[ADR-090]] (dinheiro nunca float) + [[ADR-261]] (cache invalidation).

**Capacity estimada**: ~3d eng-time.
