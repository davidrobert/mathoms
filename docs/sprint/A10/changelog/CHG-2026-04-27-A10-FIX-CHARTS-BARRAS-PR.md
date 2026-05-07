---
id: CHG-2026-04-27-A10-FIX-CHARTS-BARRAS-PR
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["de2c00a"]
summary: |
  Fix charts — barras pretas em ReceitaDespesaMensalChart (2026-04-27, [`de2c00a`](https://github.com/davidrobert/mathoms/commit/de2c00a)). - **Fix charts — barras pretas em ReceitaDespesaMensalChart (2026-04-27, [`de2c00a`](https://github.com/davidrobert/mathoms/commit/de2c00a)):** Bug visual repor
tags:
  - type/changelog-entry
  - sprint/a10
---


# Fix charts — barras pretas em ReceitaDespesaMensalChart (2026-04-27, [`de2c00a`](https://github.com/davidrobert/mathoms/commit/de2c00a))

- **Fix charts — barras pretas em ReceitaDespesaMensalChart (2026-04-27, [`de2c00a`](https://github.com/davidrobert/mathoms/commit/de2c00a)):**
  Bug visual reportado via screenshot de produção (S2 — Fluxo de Caixa):
  todas as barras renderizavam pretas, mesmo com legendas coloridas
  corretamente. Sintoma parecido com 9ce3ce2 ("cores resolvidas"),
  porém raiz diferente. **Root cause:** `--chart-1..12` definidos
  duas vezes — `tokens.css:101-112` como hex (`#1A3A5C`, ...) e
  `globals.css:58-70` como `oklch(...)`. Como `globals.css` importa
  `tokens.css` na linha 10, o cascade terminava com os `oklch()`
  ganhando. Chart.js usa `@kurkle/color@0.3.4`, que só parseia
  hex/rgb/hsl/hwb — `oklch()` é silenciosamente inválido →
  `ctx.fillStyle` cai pro default preto no canvas. Legendas (HTML+CSS)
  funcionavam porque o browser resolve `oklch()` nativamente em CSS;
  só o canvas quebrava. **Fix:** remover ambos os blocos `--chart-N`
  duplicados (light + dark) de `globals.css` — o próprio comentário
  em `globals.css:14-16` já proibia essa duplicação ("NÃO duplicar
  variáveis que já estão em tokens.css"). Cascade volta a resolver
  pelos hex de `tokens.css`. Tests 22/22 verdes (mock de Chart.js
  não capturava o bug; `LIGHT_FALLBACK` em `useChartTheme` mascarava
  o que `getComputedStyle` retornaria em produção). CAVEAT: regressão
  futura — adicionar lint que rejeite `--chart-\d+: oklch` em
  qualquer CSS é candidato a follow-up.
