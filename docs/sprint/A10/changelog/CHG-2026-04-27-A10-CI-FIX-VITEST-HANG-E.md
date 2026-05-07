---
id: CHG-2026-04-27-A10-CI-FIX-VITEST-HANG-E
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["6b09407", "10bf48b", "fd1f1fd"]
summary: |
  CI fix — Vitest hang em `ReceitaDespesaMensalChart.test.tsx` ✅ (2026-04-27). - **CI fix — Vitest hang em `ReceitaDespesaMensalChart.test.tsx` ✅ (2026-04-27):** Conserto definitivo do hang que cancelou o CI Frontend Vitest em 10min desde v2.E.6 (commit `6b09407`).
tags:
  - type/changelog-entry
  - sprint/a10
---


# CI fix — Vitest hang em `ReceitaDespesaMensalChart.test.tsx` ✅ (2026-04-27)

- **CI fix — Vitest hang em `ReceitaDespesaMensalChart.test.tsx` ✅ (2026-04-27):**
  Conserto definitivo do hang que cancelou o CI Frontend Vitest em 10min
  desde v2.E.6 (commit `6b09407`). Substitui o workaround
  `.slow.test.tsx` aplicado em `10bf48b`/`fd1f1fd` (também 2026-04-27).
  **Causa raiz:** o mock de `react-chartjs-2` em
  [ReceitaDespesaMensalChart.test.tsx](frontend/tests/components/report/ReceitaDespesaMensalChart.test.tsx)
  construía um `fakeChart` **novo a cada render** e invocava
  `props.ref?.(fakeChart)` no corpo do componente.
  [`ChartCanvas.setRef`](frontend/src/components/report/charts/primitives/ChartCanvas.tsx)
  faz short-circuit por igualdade de **referência** (`if (chartRef.current === chart) return`) —
  como cada render produzia objeto novo, `onChartReady`
  (`setChartInstance`) disparava a cada render, novo render gerava novo
  `fakeChart`, infinite render loop. Por isso testes isolados via `-t`
  passavam em <1s (1 render apenas) e o file inteiro hangava — qualquer
  teste que renderizasse o chart caía no loop.

  **Fix:**
  - `fakeChart` movido para `vi.hoisted` (singleton estável entre
    renders); o short-circuit em `ChartCanvas.setRef` agora bate.
  - Entrega do ref deferida para `useEffect` (pós-commit) em vez de
    chamada síncrona no corpo do mock — evita warning React "Cannot
    update a component while rendering a different component".
  - `beforeEach` reseta `chartUpdate.mockClear()` +
    `datasetMeta.length = 0` (cleanup antes manual em 1 teste).

  **Reversão do workaround:**
  - `git mv ReceitaDespesaMensalChart.slow.test.tsx ...test.tsx`.
  - `vitest.config.ts` — removido `"tests/**/*.slow.{test,spec}.{ts,tsx}"`
    do `exclude`.
  - `vitest.slow.config.ts` — deletado (era infra exclusiva do workaround).
  - `package.json` — script `test:slow` removido.

  **Validação:** 15/15 tests do file passam em 1.17s; suite Vitest
  completa **55 files / 646 passed + 1 skipped em 43.15s** (era cancelled
  em 10min). Sem regressões em outros test files.
