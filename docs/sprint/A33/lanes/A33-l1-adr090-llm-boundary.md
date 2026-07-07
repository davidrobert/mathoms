---
id: A33.l1
type: lane
title: "ADR-090 no boundary LLM: e15_baseline + e2_llm sem float monetário (W1β)"
sprint: A33
plan: PLAN-llm-prompts-hardening
status: open
priority: P0
branch_slug: a33-l1-adr090-llm-boundary
adrs: ["[[ADR-090]]"]
depends_on: []
parallel_with: ["[[A33.l2]]", "[[A33.l3]]"]
tags:
  - type/lane
  - sprint/a33
  - status/open
  - priority/p0
  - area/llm
---

# A33.l1 — `adr090-llm-boundary` (W1β do [[PLAN-llm-prompts-hardening]])

## Problema

`pipeline/llm/schemas/e15_baseline.py:20,31-33` declara `value_brl`,
`total_assets_brl`, `total_liabilities_brl`, `net_worth_brl` como
`float` — violação de [[ADR-090]] **no schema Pydantic do boundary LLM**,
não só no prompt. `pipeline/llm/prompts/e2_llm.py:35` instrui o modelo a
emitir formato float. O padrão correto já existe no próprio pacote:
`pipeline/llm/schemas/e16_irpf_full.py:23-35` (`_coerce_decimal`
validator). Risco mapeado pelo `data-engineer` (revisão 2026-05-22):
cadeia `extract_baseline → consolidate_baseline → e4_categorizer`
consome esses campos — a migração é de cadeia, não de arquivo.

## Escopo

1. Audit de tipos monetários em `pipeline/llm/schemas/**` (matriz do
   plano, coluna ADR-090) + auditoria do `e2_llm_extract`.
2. `e15_baseline.py`: campos monetários → `Decimal` com `_coerce_decimal`
   (padrão e16) + serializer no wire conforme ADR-090 §consequências.
3. Migração dos consumers da cadeia (`extract_baseline`,
   `consolidate_baseline`, `e4_categorizer_adapter`) com goldens
   bit-exact antes/depois — zero delta de valor em cents.
4. Prompt `e2_llm.py`: instrução de formato passa a string decimal
   explícita (mesma classe de fix da W1α no e15).
5. Gate anti-regressão: estensão do scan de float monetário
   (`dev/` — mesmo padrão do gate scan-models de [[ADR-283]]) cobrindo
   `pipeline/llm/schemas/`. Atenção ao falso positivo de naming
   (função não-monetária retornando float — precedente P5 baseline).

## Critérios de aceite

1. Zero `float` em campo monetário de `pipeline/llm/schemas/**`,
   enforçado por gate em pre-commit/CI (KR2 da sprint).
2. Goldens de execução E1.5/E1.5c verdes com valores idênticos em cents.
3. `PROMPT_VERSION` bumpado onde o texto do prompt mudou (gate
   `dev/check_prompt_version_bumped.py`, [[ADR-233]]).
4. PR(s) mergeado(s) em `main` (squash) com CI verde.
