---
id: CHG-2026-04-27-A10-FIX-CHARTS-S2-EIXO-X
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["5eb956f"]
summary: |
  Fix charts S2 — eixo X yy/mm → MMM/aa pt-BR (2026-04-27, [`5eb956f`](https://github.com/davidrobert/mathoms/commit/5eb956f)). - **Fix charts S2 — eixo X yy/mm → MMM/aa pt-BR (2026-04-27, [`5eb956f`](https://github.com/davidrobert/mathoms/commit/5eb956f)):** Bug 3 do trio reportado pelo usuário.
tags:
  - type/changelog-entry
  - sprint/a10
---


# Fix charts S2 — eixo X yy/mm → MMM/aa pt-BR (2026-04-27, [`5eb956f`](https://github.com/davidrobert/mathoms/commit/5eb956f))

- **Fix charts S2 — eixo X yy/mm → MMM/aa pt-BR (2026-04-27, [`5eb956f`](https://github.com/davidrobert/mathoms/commit/5eb956f)):**
  Bug 3 do trio reportado pelo usuário. Backend `e5_analyze.py:1311` emite
  labels de chart mensais como `"26/02"` (yy/mm), formato facilmente lido
  como `dd/MM` ("dia 26 fev"). Fix puramente no frontend (backend canônico
  é parseado por `previdencia_analyzer`, `cenarios_conjuge_analyzer`,
  `orcamento_calculator` etc. — não tocar). Helper `formatChartMonthLabel`
  em [`charts/_shared.ts`](../frontend/src/components/report/charts/_shared.ts)
  converte `"26/02"` → `"fev/26"` via regex + `MONTH_SHORT_PT_LOWER`.
  Aplicado em `FluxoMensalChart.slicedLabels` e
  `ReceitaDespesaMensalChart.sliceWindow.labels`. Outros consumidores
  (`ReceitaBarChart`, `DespesasDoughnutChart`) usam labels de fonte/
  categoria, não meses — não precisam. Vitest 3 cenários (canônico,
  não-casa, mês fora 01-12). Helper colocado em `charts/_shared.ts`
  (não em `lib/format.ts`) para ficar coeso com `fmtBRL` e evitar
  cruzar threshold T2_ts_long_files do gate code-style-baseline.
  CAVEAT: visual baselines de S2 mudam (texto eixo X diferente).
