---
id: A33.l1
type: lane
title: "ADR-090 no boundary LLM: e2_llm_extract sem float monetário + gate cobrindo pipeline/llm/schemas (W1β)"
sprint: A33
plan: PLAN-llm-prompts-hardening
status: open
ship_pr: null
ship_date: null
priority: P0
branch_slug: a33-l1-adr090-llm-boundary
adrs: ["[[ADR-090]]"]
depends_on: []
parallel_with: ["[[A33.l2]]"]
tags:
  - type/lane
  - sprint/a33
  - status/open
  - priority/p0
  - area/llm
---

# A33.l1 — `adr090-llm-boundary` (W1β do [[PLAN-llm-prompts-hardening]])

> **Reconciliado contra o código em 2026-07-07** — o texto original do
> plano (2026-05-22) apontava `e15_baseline.py`, que **já migrou** para
> `Decimal` (`_coerce_decimal`, ADR-090/ADR-259 §1). O alvo real hoje é
> o abaixo; os 4 offenders de e15 no `dev/code_style_baseline.json`
> (P5-0044..0047) são falsos-positivos stale.

## Problema

`pipeline/llm/schemas/e2_llm_extract.py` ainda declara campos
monetários como `float`: `amount` (l15), `balance_after` (l33),
`value_brl` (l47) — violação de [[ADR-090]] no schema Pydantic do
boundary LLM. `pipeline/llm/prompts/e2_llm.py:35` instrui o modelo a
emitir formato float. O padrão correto existe no próprio pacote
(`e15_baseline._coerce_decimal`). E o gate `dev/check_float_money.py`
só escaneia `backend/app/models` — é cego para `pipeline/llm/schemas/`:
regressão de Decimal→float no boundary LLM passaria silenciosa.

## Escopo

1. `e2_llm_extract.py`: `amount`/`balance_after`/`value_brl` → `Decimal`
   com `_coerce_decimal` (padrão e15/e16); `confidence` permanece float
   (não-monetário).
2. Migração dos consumers do payload E2-llm (adapter E2→E3 e
   serialização) com goldens bit-exact antes/depois — zero delta de
   valor em cents.
3. Prompt `e2_llm.py`: instrução de formato passa a string decimal
   explícita + bump de `PROMPT_VERSION` (gate
   `dev/check_prompt_version_bumped.py`, [[ADR-233]]).
4. **Auditoria** `parecer_planejador.py:252` (`valor_estimado_brl:
   float` com WHY deliberado "Instructor é float; cents on persist") —
   decidir com `data-engineer` se migra ou se a exceção documentada
   fica; registrar a decisão no PR, não mudar às cegas.
5. Gate anti-regressão: estender `dev/check_float_money.py` (ou scan
   irmão) para cobrir `pipeline/llm/schemas/`, **herdando a allowlist
   do scan-models de [[ADR-283]]** (não reinventar) — campos
   não-monetários (`confidence`, bounds `ge`/`le`) e exceções
   documentadas ficam fora. Atenção ao falso positivo de naming
   (função não-monetária retornando float — precedente P5 baseline).
6. `pipeline/llm/validators.py:486-490`: tolerância `> 1.0` (float
   literal sobre aritmética `Decimal`, tolera 99 centavos silenciosos)
   → comparação em cents inteiros ou `Decimal` explícito.
7. Rebaseline: remover os 4 offenders stale de e15 do
   `dev/code_style_baseline.json` (commit separado, formatter-only
   discipline).

## Critérios de aceite

1. Zero `float` em campo monetário de `pipeline/llm/schemas/**` (fora
   de exceção documentada com WHY), enforçado por gate em pre-commit/CI
   (KR2 da sprint).
2. Golden da cadeia real do payload: `extract_with_llm` → E3
   reconciliado (não E1.5 — o e15 já migrou) com valores idênticos em
   cents antes/depois.
3. `PROMPT_VERSION` bumpado onde o texto do prompt mudou.
4. PR(s) mergeado(s) em `main` (squash) com CI verde.
