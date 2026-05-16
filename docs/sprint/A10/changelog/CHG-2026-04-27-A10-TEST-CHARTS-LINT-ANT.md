---
id: CHG-2026-04-27-A10-TEST-CHARTS-LINT-ANT
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["de2c00a"]
summary: |
  Test charts — lint anti-regressão `--chart-N: oklch(…)` (2026-04-27). - **Test charts — lint anti-regressão `--chart-N: oklch(…)` (2026-04-27):** Follow-up do CAVEAT registrado no fix `de2c00a` (barras pretas RDM).
tags:
  - type/changelog-entry
  - sprint/a10
---


# Test charts — lint anti-regressão `--chart-N: oklch(…)` (2026-04-27)

- **Test charts — lint anti-regressão `--chart-N: oklch(…)` (2026-04-27):**
  Follow-up do CAVEAT registrado no fix `de2c00a` (barras pretas RDM).
  Novo spec em
  [`frontend/tests/styles/chart-vars-no-oklch.test.ts`](../../../../frontend/tests/styles/chart-vars-no-oklch.test.ts)
  varre `frontend/src/**/*.css` e falha se qualquer `--chart-\d+`
  estiver definido com `oklch()`, `oklab()`, `lab()` ou `lch()` —
  funções que `@kurkle/color@0.3.4` (parser do Chart.js) não suporta,
  produzindo `ctx.fillStyle` inválido e canvas preto. O teste
  componente existente em
  [`ReceitaDespesaMensalChart.test.tsx:274-301`](../../../../frontend/tests/components/report/ReceitaDespesaMensalChart.test.tsx)
  só pega literal `var(...)` no dataset; em jsdom `useChartTheme`
  cai pro `LIGHT_FALLBACK` (hex hard-coded), então regressão na CSS
  escapava. Verificado revertendo `de2c00a` localmente: 24 ofensores
  flagged, fix-forward retornou 4/4 verdes.
