---
id: CHG-2026-04-27-A10-FIX-CHARTS-S2-CORES
type: changelog-entry
date: "2026-04-27"
sprint: A10
summary: |
  Fix charts S2 — cores resolvidas + eixo Y (2026-04-27). - **Fix charts S2 — cores resolvidas + eixo Y (2026-04-27):** Bugs visuais reportados via screenshots de produção em `ReceitaDespesaMensalChart` e `FluxoMensalChart` (S2 — Fluxo de Caixa).
tags:
  - type/changelog-entry
  - sprint/a10
---


# Fix charts S2 — cores resolvidas + eixo Y (2026-04-27)

- **Fix charts S2 — cores resolvidas + eixo Y (2026-04-27):** Bugs visuais
  reportados via screenshots de produção em `ReceitaDespesaMensalChart`
  e `FluxoMensalChart` (S2 — Fluxo de Caixa). **Bug 1 (cores pretas):**
  ambos os charts passavam literais `var(--chart-N)` / `var(--semantic-gain)`
  como `backgroundColor` ao Chart.js — Chart.js não resolve CSS vars no
  canvas (apenas no DOM, motivo pelo qual a legenda `RDMLegend` mostrava
  cores corretas mas o canvas ficava preto). Fix: `useChartTheme()`
  estendido com `theme.semantic.{gain,loss}` (resolvidos via
  `getComputedStyle`); `ReceitaDespesaMensalChart` consome
  `theme.categorical` em vez de `pickColorByIndex` (que retorna literal
  `var(...)`); `FluxoMensalChart` consome `theme.semantic`. **Bug 2
  (eixo Y):** (a) `ReceitaDespesaMensalChart` começava em `-R$ 20k`
  mesmo sem valores negativos — fix `beginAtZero: true` no scale `y`;
  (b) `FluxoMensalChart` duplicava label "R$ 50.000" sem sinal `−` no
  negativo (bipolar ok, mas formatter aplicava `Math.abs`) — fix
  removendo `Math.abs` em `formatValue`. `pickColorByIndex` marcado
  `@deprecated` (mantido por compat com `PatrimonioDoughnutChart`/
  `ReceitaBarChart`/`DespesasDoughnutChart`). Anti-regressão Vitest:
  novos testes garantem `dataset.backgroundColor` jamais começa com
  `"var("`. **CAVEAT:** visual baselines de S2
  (`S2-light-visual-linux.png`, `S2-dark-visual-linux.png`) precisam
  refresh em próxima rodada de visual gate via humano com
  `update_visual_baselines=true` — preto → colorido e Y-axis zerado
  mudam pixel rendering.
