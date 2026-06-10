---
id: A25.l4
type: lane
title: "Data Lineage F7 — debug substrate LLM: renderer, lineage_diff, tools, eval"
sprint: A25
plan: PLAN-data-lineage
status: open
priority: P0
branch_slug: dl-f7-debug-llm
adrs:
  - "[[ADR-281]]"
depends_on: []
parallel_with: ["[[A25.l1]]", "[[A25.l3]]", "[[A25.l5]]"]
tags:
  - type/lane
  - sprint/a25
  - status/open
  - priority/p0
  - area/data-lineage
  - area/llm
---

# A25.l4 — `dl-f7-debug-llm` (F7 · ancora KR1/KR3)

> **Plano:** [[PLAN-data-lineage]] · §Arquitetura G. Conforma à [[ADR-281]]; não
> reabre. **Só precisa do `_lineage` forward que JÁ existe** — abre já.
> Precedência de corte da sprint: **F7 > F6**.

## Objetivo

Substrato de debug consumível por LLM: renderer de trace linearizada +
`lineage_diff` + tools + eval de injeção determinística de bug.
KR1 `localization_accuracy@node ≥ 85%` · KR3 `tool_iterations_p95 ≤ 6`.

## Decisões de co-design (prompt-engineer + senior-cto, 2026-06-10 — travadas)

1. **Superfície:** tudo função de domínio pura em `pipeline/domain/services/`
   (renderer `render_lineage_linear` ao lado do humano em `lineage_render`;
   `lineage_diff`; tools) + cascas CLI em `dev/` (padrão `dev/explain_number.py`).
   **Zero código em `backend/app/api/`** — MCP prod DEFERIDO ([[ADR-281]]).
2. **Renderer:** template ~40-55 tok/nó
   `[N] {field} = {value} | {label} | {transform} [{edge_type}]` + linha de inputs
   `#N`/rule/⚠anomalia (omitida em nó limpo). Anomaly-first em 2 passadas (BFS →
   emite ⚠ primeiro). **Colapso de subárvore**: todos os descendentes `lineage`
   (sem `dangling`), `needs_review=false`, `range_check ∈ (ok, absent)` e conservação
   local fecha em cents int → 1 linha `✓ (K nós, sem anomalia)`. Teto 1.5k tokens.
3. **Eval — suite de injeção:** mutação programática do payload golden **em memória**
   (nunca disco); ground truth = `node_id` canônico `(stage, artifact_key, field)`.
   **24 casos = 6 famílias × 4** (value_delta@leaf, value_delta@aggregate,
   input_removed, rule_ref_wrong, dedup_overcollapse, needs_review_ignored)
   **+ 5 casos "selados"** dos bugs históricos ([[ADR-271]]/[[ADR-246]]/[[ADR-255]]/
   R$ 811k/membro-CPF) não-tunáveis (anti-Goodhart). PII-sintético.
4. **Harness:** `localize(tree_b, tree_a) → LocalizationResult` — 1 chamada Anthropic
   + loop de tools capado a 6 (reusa a mecânica do tool-loop do parecer). Structured
   output Pydantic; parse-fail 2× = miss, não crash. N=3 trials/caso + flag
   `trials_agreement` (follow-up `seed` **entregue**: PR #606 expôs `seed` em
   `LLMService.call`; harness pina `seed: 281` no YAML — best-effort, provider
   sem suporte descarta via `drop_params`). Model pinado **literal**
   `anthropic/claude-sonnet-4-20250514` (snapshot datado, já é o pin de prod) em YAML
   próprio; temp=0.
5. **Eval roda em NIGHTLY (G-g), não em PR.** PR roda só os goldens determinísticos
   (renderer, `lineage_diff`, `check_lineage_refs`). Mecânica de bloqueio real:
   nightly compara contra baseline commitada
   (`dev/snapshots/lineage_eval_baseline.json`); falha se `<85%` OU `< baseline−2pp`
   → abre Issue auto com label `lineage-eval-fail` → gate PR-time **determinístico**
   `dev/check_lineage_eval_gate.py` falha em PRs que tocam a área lineage enquanto a
   Issue estiver aberta. Baseline atualizada só por dispatch deliberado.
6. **Custo:** cap duro **$5.00/run** (agregado de `_meta.cost_usd` dos ~87 calls;
   per-call soft $0.10); skip sem `ANTHROPIC_API_KEY` (degrada p/ determinístico).
   Estimativa: típico ~$1.4/run, 3×/semana ≈ $4-10/mês.
7. **Telemetria:** artefato de CI 30d (JSON por caso) + baseline agregada commitada
   (`accuracy global+por família, p95, tokens, custo, model_id`); logs
   `mathoms.llm.lineage_eval`.

## Critério de aceite

- `lineage_diff` puro com golden determinístico (nós mudados + first-divergent-leaf
  + propagação) — PR-gate.
- `render_lineage_linear`: golden de formato (anomaly-first, colapso, ≤1.5k tokens).
- Suite 24+5 casos; KR1 ≥85% no nightly com baseline commitada; KR3 p95 ≤6.
- `check_lineage_eval_gate` + Issue-sentinela funcionando (testado com Issue fake).
- Cap de custo + skip sem key; zero PII nas fixtures.
- Follow-up `seed` no `litellm_client` registrado — **entregue** (PR #606 client +
  plumbing no harness/YAML).

## Owner

Agente da lane; co-design `prompt-engineer` + `senior-cto` (2026-06-10).
