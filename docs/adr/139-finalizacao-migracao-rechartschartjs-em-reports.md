---
id: ADR-139
type: adr
title: "Finalização migração Recharts→Chart.js em /reports/**"
status: Decidido
phase: "Onda v2.E concluída"
date: "2026-04-26"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 139"]
tags:
  - area/frontend
  - area/llm
  - area/report
  - status/decidido
  - type/adr
size_lines: 104
---

# ADR-139 — Finalização migração Recharts→Chart.js em /reports/**

**Status:** Decidido (Onda v2.E concluída) • **Data:** 2026-04-26

**Contexto:** ADR-117 (Fase 2) entregou primitives Chart.js
(`frontend/src/components/report/charts/primitives/` —
`ChartCanvas`, `ChartBar`, `ChartDonut`, `ChartGaugeSemi`, `ChartCombo`,
`ChartLine`, `ChartWaterfall`, `ChartRegistry` com print fallback
canvas→PNG e tema via `useChartTheme`), mas a Fase 7 do
[REPORT_PREMIUM_PLAN](../plan/REPORT_PREMIUM/_README.md) **não fechou** a
substituição efetiva nas seções — charts Lote A/B
(`FluxoMensalChart`, `ReceitaBarChart`, `DespesasDoughnutChart`,
`ReceitaDespesaMensalChart`, `ScoreGaugeChart`) continuaram em Recharts,
e o gauge profissional (`ScoreCard` pronto em
`frontend/src/components/report/ui/`) ficou sem ser plugado em S1.
Onda v2.E executou esse fechamento em 8 sub-lanes paralelizáveis (até 4
agentes simultâneos em worktrees isoladas).

**Decisão:** Onda v2.E entregou (8/8 sub-lanes em main 2026-04-26):

- **5 charts migrados Recharts→Chart.js:**
  - `FluxoMensalChart` (v2.E.3, `5b8d54a`),
  - `ReceitaBarChart` (v2.E.4, `0e07499`),
  - `DespesasDoughnutChart` (v2.E.5, `6d0ab67`),
  - `ReceitaDespesaMensalChart` (v2.E.6, `6c2efc4`+`f8cb30f`+`6b09407`+`32089ce`+`d9fa765`+`358d5ea`),
  - `ScoreCard` plugado em S1 (v2.E.7, `55f00fa`+`22ca7d0`+`334f5f7`+`529cd70`)
    com `ScoreGaugeChart.tsx` deletado.
- **`PeriodToggle`** (3M/6M/12M/Ano, v2.E.1, `da841c2`) introduzido em
  `FluxoMensal`/`ReceitaBar`/`DespesasDoughnut`. `ReceitaDespesaMensal`
  usa **slide window 12m** com prev/next/dots em vez do toggle —
  decisão de paridade visual com `EXEMPLO_DE_RELATORIO.html:1797-1803`.
- **`usePeriodWindow`** hook puro em
  `frontend/src/components/report/hooks/` (v2.E.1) e **`useIsPrint`**
  hook em `frontend/src/components/report/hooks/` (v2.E.3) reaproveitado
  pelos 4 charts da leva 2.
- **`pickColorByIndex`** em `_shared.ts` para paleta estável por índice
  (v2.E.5).
- **`ChartDonut`** ganhou prop opcional `dataLabelFormatter` (v2.E.5);
  **`ChartCanvas`** ganhou prop opcional `onChartReady` (v2.E.6) —
  extensões aditivas, backwards-compat.
- **TS types `receita_datasets`/`despesa_datasets`** em
  `FluxoCaixaSummary` (v2.E.2, `8ee4bd6`) — `ChartSeries` em
  `frontend/src/types/chart-series.ts` (separado de
  `primitives/types.ts::ChartSeries` para evitar colisão).
- **Backend `financial_score_calculator`** agora emite `breakdown` /
  `formula` / `context` / `conclusion` (v2.E.7); preferência por
  `narrativas[score_gauge].conclusion` (E5.N LLM) sobre template
  determinístico — alinhamento com ADR-122.
- **Slide window 12m + tooltip por stack + legenda agrupada custom**
  (`RDMLegend`) em `ReceitaDespesaMensal` (v2.E.6) — paridade exata
  com `EXEMPLO_DE_RELATORIO.html:7756-7939`.
- **v2.5 (`report-v2-score-dto`) absorvida em v2.E.7** — `score?:
  ScoreData` top-level em `ReportAnalysisData`; `ScoreData` ganhou
  `context?` e `conclusion?`; zero `as ScoreData` no codebase.

**Fora de escopo (intencional — preservado):**

- `WaterfallIfChart.tsx` e `PatrimonioDoughnutChart.tsx` continuam em
  Recharts dentro de `/reports/**`. Migração pode virar **v2.E.9**
  futura se produto pedir paridade.
- Recharts permanece em `frontend/src/components/charts/Mathom*.tsx` e
  `frontend/src/app/(app)/plano/_components/_dashboard/` (caminho atual
  do antigo `dashboard/_components/`) — ADR-037 com escopo
  restringido.

**Coordenação multi-agente empiricamente validada:** segunda leva da
Onda v2.E rodou 4 agentes simultâneos em worktrees isoladas, com 3
colisões em hotspots todas resolvidas via convergência em rebase
(zero perda):

- `useIsPrint.ts` — E.3 venceu; E.4/E.5/E.6 convergiram para a versão
  já em main.
- `pickColorByIndex` em `_shared.ts` — E.5 venceu; E.4 dropou commit
  duplicado idêntico em rebase.
- `ChartCanvas.tsx` — E.6 fez extensão aditiva (`onChartReady`) sem
  conflito.

**Anomalia aprendida:** v2.E.6 pulou gates locais (worktree sem
`node_modules` / `pre-commit`) e confiou no CI como gate efetivo → 2
funções TS >20 linhas detectadas pós-merge → cleanup follow-up
`d9fa765` extraiu helpers (`enrichSeriesForStack`, `formatMoneyAxisTick`)
+ baseline atualizada em `358d5ea` com bonus colateral T5_ts_hex_colors
−2 das 4 migrações da onda. Lição: prompts futuros devem exigir gate
local **ou** explicitar fallback quando `node_modules` indisponível.

**Consequências:**

- ✅ Paridade visual exata com `EXEMPLO_DE_RELATORIO.html` para os 5
  charts mais visíveis do relatório (Score, Fluxo Mensal, Receita
  Bar, Despesas Doughnut, Receita vs Despesa Mensal).
- ✅ Bundle Recharts pode ser parcialmente tree-shaken se nenhuma
  rota fora de `/reports/**` usá-lo — não é o caso atual
  (`MathomBarChart`, `MathomPieChart`, `MathomAreaChart` em
  `frontend/src/components/charts/` ainda usam).
- ✅ Coordenação multi-agente em hotspots compartilhados validada
  empiricamente (3 colisões resolvidas) — protocolo
  CLAUDE.md §Hotspots funcionou para esta sprint.
- ⚠️ `WaterfallIfChart` e `PatrimonioDoughnutChart` continuam em
  Recharts — divergência visual aceita até v2.E.9 (se ocorrer).

Relaciona-se a: ADR-037 (Recharts — escopo restringido), ADR-076
(design tokens), ADR-117 (Report Premium UI baseline), ADR-122
(`chart_conclusions` em modo híbrido template+LLM).
