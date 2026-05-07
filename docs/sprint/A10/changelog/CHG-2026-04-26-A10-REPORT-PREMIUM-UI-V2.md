---
id: CHG-2026-04-26-A10-REPORT-PREMIUM-UI-V2
type: changelog-entry
date: "2026-04-26"
sprint: A10
adrs: ["[[ADR-037]]", "[[ADR-076]]", "[[ADR-117]]", "[[ADR-122]]", "[[ADR-139]]"]
commits: ["da841c2", "8ee4bd6", "55f00fa", "22ca7d0", "334f5f7", "529cd70", "5b8d54a", "0e07499", "d2ae024", "6d0ab67", "6c2efc4", "f8cb30f", "6b09407", "32089ce", "d9fa765", "358d5ea"]
summary: |
  Report Premium UI v2 — Onda E (Charts UX) ✅ 8/8 (2026-04-26). - **Report Premium UI v2 — Onda E (Charts UX) ✅ 8/8 (2026-04-26):** Onda E fechou a migração Recharts→Chart.js dentro de `/reports/**` que [ADR-117](DECISIONS.m
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Premium UI v2 — Onda E (Charts UX) ✅ 8/8 (2026-04-26)

- **Report Premium UI v2 — Onda E (Charts UX) ✅ 8/8 (2026-04-26):**
  Onda E fechou a migração Recharts→Chart.js dentro de `/reports/**`
  que [ADR-117](DECISIONS.md#adr-117--report-premium-ui-baseline-paridade-com-exemplo_de_relatoriohtml)
  Fase 2 abriu mas Fase 7 não fechou. **8 sub-lanes** documentadas em
  [track_report_v2_charts_ux.md](agent_prompts/track_report_v2_charts_ux.md);
  duas levas paralelas (3+4 agentes simultâneos em worktrees
  isoladas) + closeout sequencial; todas mergeadas em main no mesmo
  dia. Decisão consolidada em
  [ADR-139](DECISIONS.md#adr-139--finalização-migração-recharts→chart.js-em-reports).

  **Leva 1 (3 agentes paralelos):**
  - ✅ **v2.E.1** — `PeriodToggle` UI primitive + hook `usePeriodWindow`
    (commit `da841c2`). Segmented control 3M/6M/12M/Ano portado para
    tokens (`--brand-primary`, `--surface-card`, `--surface-border`),
    paridade `EXEMPLO_DE_RELATORIO.html:381-413`. Hook puro suporta
    formato `"YY/MM"` e `"mes/aa"` pt-BR. 16 specs Vitest (10 hook + 6
    componente) em `frontend/tests/components/report/` (config vitest
    exige). Enabler de v2.E.3/E.4/E.5.
  - ✅ **v2.E.2** — TS types `receita_datasets`/`despesa_datasets`
    em `FluxoCaixaSummary` (commit `8ee4bd6`). Tipo `ChartSeries` em
    `frontend/src/types/chart-series.ts` (separado de
    `primitives/types.ts::ChartSeries` para evitar colisão).
    **Divergência registrada:** backend hoje só emite `{label, data}`
    por dataset; `backgroundColor`/`stack`/`borderRadius` opcionais —
    enriquecimento client-side fica em E.4-E.6. Enabler de
    v2.E.4/E.5/E.6.
  - ✅ **v2.E.7** — `ScoreCard` premium plugado em S1 + score top-level
    no DTO + backend `score.context`/`score.conclusion` (commits
    `55f00fa` + `22ca7d0` + `334f5f7` + `529cd70`). **Absorve v2.5**
    (score-dto). `S1PatrimonioSection` consome `<ScoreCard/>` (era
    `<ScoreGaugeChart/>` Recharts); `ScoreCardProps` ganhou `context?`
    e `conclusion?` com classes CSS `chart-context`/`chart-conclusion`.
    Backend `financial_score_calculator` agora emite `breakdown`
    (renomeado de `componentes` — peso normalizado fração [0..1] +
    `contribuicao` calculada), `formula`, `context`, `conclusion`.
    Templates Python determinísticos paridade
    `EXEMPLO_DE_RELATORIO.html:1809-1811`; top-2 drivers em `conclusion`
    ranked por `contribuicao`. Frontend prefere
    `narrativas[score_gauge]?.conclusion` (E5.N LLM) sobre
    `score.conclusion` (template) — alinhamento com
    [ADR-122](DECISIONS.md#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm).
    `ScoreGaugeChart.tsx` deletado; `_registry.ts` limpo. Vitest 593
    passed; `pytest tests` 1470; `pytest backend/tests` 1324. Zero
    `as ScoreData` ou `ScoreGaugeChart` em `frontend/src/`.

  **Leva 2 (4 agentes paralelos simultâneos):**
  - ✅ **v2.E.3** — `FluxoMensalChart` Recharts→Chart.js stacked +
    `PeriodToggle` + `usePeriodWindow` (commit `5b8d54a`). 7 specs
    Vitest novas (5 chart + 2 hook); 610 testes passed; pre-commit
    verde. **Side-effect positivo:** criou
    `frontend/src/components/report/hooks/useIsPrint.ts`
    (`matchMedia("print")` + listener SSR-safe) — reaproveitado por
    E.4/E.5/E.6.
  - ✅ **v2.E.4** — `ReceitaBarChart` Recharts→Chart.js horizontal +
    `PeriodToggle` (commit `0e07499`). Consome `receita_datasets[]`
    somando dentro da janela escolhida; ordenação desc por total;
    paleta estável via `pickColorByIndex`; 9 specs Vitest; 628 testes
    passed. **Hotspot resolvido:** commit `d2ae024` (helper duplicado)
    foi **dropado durante rebase** após v2.E.5 entrar primeiro com
    função idêntica — protocolo CLAUDE.md §Hotspots funcionou
    automaticamente.
  - ✅ **v2.E.5** — `DespesasDoughnutChart` Recharts→Chart.js +
    datalabels + `PeriodToggle` (commit `6d0ab67`). Consome
    `despesa_datasets[]` somando por janela; datalabels `R$ Xk` para
    fatias ≥5%; `cutout: '50%'`; fallback gracioso em
    `despesas_por_categoria` agregado quando datasets ausentes (toggle
    oculto nesse caminho); 9 specs Vitest; 612 testes passed.
    **Side-effects positivos:** (a) criou helper `pickColorByIndex`
    em `_shared.ts` (módulo 12, estável por índice — reutilizado por
    E.4/E.6); (b) `ChartDonut` primitive ganhou prop opcional
    `dataLabelFormatter(value, pct, label)` + `textStrokeColor`/
    `textStrokeWidth` (extensão aditiva, backwards-compat).
    **Conflito resolvido:** rebase em `useIsPrint.ts` adotou versão
    canônica de E.3 já em main.
  - ✅ **v2.E.6** — `ReceitaDespesaMensalChart` Recharts→Chart.js
    stacked + slide window 12m + tooltip por stack + legenda agrupada
    custom + Vitest + E2E Playwright `@critical` (commits `6c2efc4` +
    `f8cb30f` + `6b09407` + `32089ce` + cleanup `d9fa765` + baseline
    `358d5ea`). Bar empilhado com 2 stack groups (`receita`/`despesa`),
    enriquecimento client-side de `backgroundColor` via
    `pickColorByIndex` e `stack` derivado do array de origem; slide
    window 12m com prev/next + dots (oculto se ≤12m); tooltip custom
    apenas do stack hovered (title/body/footer paridade
    `EXEMPLO_DE_RELATORIO.html:7798-7829`); `RDMLegend.tsx` (legenda
    agrupada Receitas/Despesas, swatches clicáveis com
    `data-legend-swatch`/`aria-pressed`); chart-context +
    chart-conclusion auto-gerados; print mode oculta nav/legenda
    interativa, fixa última janela 12m, renderiza bloco textual de
    totais consolidados; `ChartCanvas` ganhou prop
    `onChartReady?(chart)` opcional (extensão aditiva).
    **Anomalia aprendida:** agente pulou gates locais (worktree sem
    `node_modules`/`pre-commit`) e confiou no CI como gate efetivo →
    2 funções TS >20 linhas detectadas pós-merge na branch principal
    (`useEnrichedDatasets` 26 linhas, `buildOptions` 25 linhas) →
    cleanup follow-up `d9fa765` extraiu helpers
    `enrichSeriesForStack` e `formatMoneyAxisTick` (sem mudança de
    comportamento) + baseline atualizado em `358d5ea`. Lição para
    futuros prompts: exigir gate local ou explicitar fallback quando
    `node_modules` indisponível.

  **Closeout sequencial:**
  - ✅ **v2.E.8** — cleanup imports Recharts em `_registry.ts`
    (header atualizado refletindo Chart.js 4 + Recharts intencional
    para `WaterfallIfChart`/`PatrimonioDoughnutChart`); ADR-139
    "Finalização migração Recharts→Chart.js em /reports/**" gravada
    em main relacionando-se a ADR-037, ADR-076, ADR-117, ADR-122;
    BACKLOG/CHANGELOG sincronizados. Verificação por grep: `from
    "recharts"` em `frontend/src/components/report/charts/` retorna
    apenas os 2 charts intencionais. **Re-baseline visual delegada
    ao operador humano:** workflow `frontend-visual` opt-in
    (`gh workflow run CI -f run_visual=true
    -f update_visual_baselines=true`) exige permissão `gh` ausente
    do sandbox do agente; baselines esperadas mudarem: cover×2 +
    S1×2 + S2×2 = 6 PNGs; restantes (40 PNGs S3-S10/T*/U*/APP_*)
    idênticos.

  **Coordenação de hotspot empiricamente validada** entre os 4
  agentes paralelos da Leva 2:
  - `useIsPrint.ts` — E.3 venceu (criou primeiro); E.4/E.5/E.6
    convergiram via rebase.
  - `pickColorByIndex` em `_shared.ts` — E.5 venceu; E.4 detectou
    duplicação idêntica no rebase e dropou commit (sem perda).
  - `ChartCanvas.tsx` — E.6 fez extensão aditiva (`onChartReady?`)
    sem conflito.

  **Bonus colateral:** T5_ts_hex_colors baseline -2 (4 migrations
  removeram hex literals em favor de tokens `var(--brand-*)`/
  `pickColorByIndex`).

  **Fora de escopo (preservado intencionalmente — eventual v2.E.9):**
  `WaterfallIfChart.tsx` e `PatrimonioDoughnutChart.tsx` continuam em
  Recharts. Recharts permanece também em
  `frontend/src/components/charts/Mathom*.tsx` e
  `frontend/src/app/(app)/dashboard/_components/`
  ([ADR-037](DECISIONS.md#adr-037--recharts-para-charts) com escopo
  restringido).
