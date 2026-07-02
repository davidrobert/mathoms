---
id: TRACK-a3cli-benchmark
type: track
title: "Track A3.cli.benchmark — gate empírico de cold start do run-stage (decide se Caminho 2 reabre antes do 1º PR Go)"
plan: PLAN-go-shell
status: consumed
created_at: "2026-07-02"
consumed_at: "2026-07-02"
agent_role: senior-cto
tags:
  - type/track
  - area/pipeline
  - status/consumed
  - priority/p2
---

# Track A3.cli.benchmark — `a3cli-benchmark`

> **Status 2026-07-02 — CONSUMED: gate PASSA.** Cold start mediana **413ms ≤ 500ms
> → Caminho 1 segue**; p95 830ms; acumulado projetado 4,1s/run determinístico e
> 7,4s/run full — dentro da estimativa da ADR-150 e abaixo do risco de 10s.
> Números, método e breakdown de imports:
> [PERFORMANCE_BASELINE §11](../../../reference/PERFORMANCE_BASELINE.md); script
> `dev/benchmark_run_stage_cold_start.py`.
>
> ~~⛔ GATE DE PICKUP: não iniciar antes das 2 fases de
> [TRACK-a3cli-orchestrator-cli](a3cli-orchestrator-cli.md) mergeadas em `main`~~
> (cumprido: #737 + #738).
>
> **Tipo:** gate de **medição com critério de decisão** ([[ADR-150]] §4
> A3.cli.benchmark), não feature. **Branch prefix:** `agent/a3cli-benchmark/*`.
> **Tese:** boot Python real não é `python -c pass` (~50ms) — é o re-import da
> árvore de domínio (38k LOC), que o baseline A2 **não mediu** (imports lazy).
> O número decide se o Caminho 1 segue ou se o Caminho 2 (worker pool warm)
> reabre **antes** do primeiro PR Go — não depois.

## O que medir

Ambiente: venv produtivo completo (deps de `pipeline.*`, `pipeline.llm.*`,
`backend.*` instaladas), máquina descrita no relatório (mesmo protocolo do
[PERFORMANCE_BASELINE](../../../reference/PERFORMANCE_BASELINE.md)).

1. **Métrica de gate (decisão binária)** — cold start de **um**
   `python -m pipeline.orchestrator run-stage` isolado: tempo do `exec` até o
   primeiro byte do JSON no stdout, para um stage não-LLM barato contra fixture
   sintética PII-zero. **N ≥ 20 amostras frias** (sem warm-up reaproveitado);
   reporte **mediana + p95**. Separe, se instrumentável, import-time vs
   execução do stage (ex.: `-X importtime` numa amostra).
2. **Métrica de impacto (contexto, obrigatória)** — overhead acumulado projetado
   para um run E0→E5 típico: `N stages × mediana` (use a cardinalidade real do
   `DETERMINISTIC_ORDER`/`FULL_ORDER` — 18 stages hoje). **Baseline explícito =
   caminho in-process atual** (`InProcessPipelineClient`/Celery, overhead
   fork+exec ≈ 0) — não compare contra o modo HTTP. A [[ADR-150]] §Consequências
   estima 6-13s/run; confirme ou refute.
3. **Método reprodutível** — script committed em `dev/` (ex.
   `dev/benchmark_run_stage_cold_start.py` ou hyperfine documentado) + comando
   exato no relatório, para refalsificar na revisita da ADR-150 (2027-Q2 / 100
   workspaces pagantes).

## Critério de decisão (falsificável, da [[ADR-150]] §4 — não renegociar aqui)

- **Mediana ≤ 500ms** → Caminho 1 segue como default; registrar o número.
- **Mediana > 500ms** → **Caminho 2 (worker pool warm) volta à mesa ANTES do
  primeiro PR Go produtivo**: abrir emenda na [[ADR-150]] registrando o número
  e reabrindo a comparação Caminho 1 vs 2 (decisão nova é do `senior-cto` +
  owner — este track só mede e reporta).
- Em ambos os casos: se o **acumulado por run** projetado tornar o loop de
  dogfood iterativo intolerável (>10s de overhead/run), registre como risco
  destacado na emenda/relatório mesmo com o gate por-stage passando — a métrica
  por-stage decide o gate; a acumulada decide se o Caminho 1 sobrevive ao
  primeiro dia de uso real.

## Entregáveis (docs-only + script; concluído = PR mergeado)

- [x] Seção "§11 A3.cli.benchmark (2026-07-02)" no
      [PERFORMANCE_BASELINE](../../../reference/PERFORMANCE_BASELINE.md):
      mediana 413ms, p95 830ms, N=20, Apple M4/Python 3.12, breakdown
      `-X importtime`, acumulado 4,1–7,4s/run vs baseline in-process ≈ 0.
- [x] Decisão binária documentada (≤500ms → Caminho 1 segue) + ✅ na
      [[ADR-150]] §4 (com o número) e no F0 do [_README do plano](../_README.md);
      `GO_PORT_DEPS.md` §6 atualizado.
- [x] ~~Se >500ms: emenda reabrindo Caminho 2~~ — não disparou (413 ≤ 500).
- [x] Script de medição: `dev/benchmark_run_stage_cold_start.py`.

## Fora de escopo

- Otimizar o cold start (lazy imports adicionais etc.) — se o número reprovar,
  a resposta é a emenda/decisão, não micro-otimização silenciosa neste track.
- Qualquer código Go; qualquer mudança no CLI além de instrumentação opcional
  de medição.
