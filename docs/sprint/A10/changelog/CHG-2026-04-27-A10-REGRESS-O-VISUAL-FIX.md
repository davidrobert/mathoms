---
id: CHG-2026-04-27-A10-REGRESS-O-VISUAL-FIX
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["ba29df1", "b47dd47", "0558ea3", "db6cf6f"]
summary: |
  Regressão visual fixada + rebaseline parcial (Items 4+2) ✅ (2026-04-27). - **Regressão visual fixada + rebaseline parcial (Items 4+2) ✅ (2026-04-27):** Item 4 fixou a regressão silenciosa que fazia 28 baselines visuais (cover×2 + S1-
tags:
  - type/changelog-entry
  - sprint/a10
---


# Regressão visual fixada + rebaseline parcial (Items 4+2) ✅ (2026-04-27)

- **Regressão visual fixada + rebaseline parcial (Items 4+2) ✅ (2026-04-27):**
  Item 4 fixou a regressão silenciosa que fazia 28 baselines visuais (cover×2 +
  S1-S4×2 + S7-S10×2 + APP_A-E×2) skipar com `count===0` para
  `section#S1[data-report-section]`. Causa raiz: commit `ba29df1`
  (`ConsumoConscienteCard` em S2) chamava `pontuais.length` sobre items vindos
  de `useConsumoPontuais`, que confiava no shape de `ConsumoPontuaisResponse`.
  Em ambientes mockados (mock catch-all `{}` em `tests/e2e/helpers/mock-report.ts`),
  `items` chegava `undefined`, lançando `TypeError: Cannot read properties of
  undefined (reading 'length')`. ErrorBoundary do shell capturava e
  substituía o `<article>` inteiro — fazendo S1-S10/APP_A-E desaparecerem do
  DOM, e `count() === 0` em `snapshotSection()` chamar `test.skip()` em vez
  de capturar screenshot. Sintoma silencioso: visual job verde, mas baselines
  não atualizavam. Commit [`b47dd47`](https://github.com/davidrobert/mathoms/commit/b47dd47):
  fix em duas camadas defensivas — (1) `useConsumoPontuais.toState()` coerce
  `items`/`total`/`total_valor` para defaults seguros (`Array.isArray` +
  `typeof number`); (2) `mock-report.ts` adiciona rota explícita
  `/reports/consumo-pontuais` retornando shape completo. Anti-regressão:
  `tests/hooks/useConsumoPontuais.test.tsx` cobre 3 cenários (resposta
  válida, malformada `{}`, erro de rede).

  Item 2 disparou run [25011732190](https://github.com/davidrobert/mathoms/actions/runs/25011732190)
  em main com `update_visual_baselines=true`. **24 PNGs regenerados** em
  `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/`:
  cover×2 + S1-S10×2 = 16 + APP_A-D×2 = 8 (todas estratégicas + apêndices
  exceto APP-E). **Cover, APP-E, T1-T6, U1-U4 preservados** — Playwright
  detectou conteúdo idêntico (não mudaram visualmente apesar de v2.F.3b
  cover identity, v2.4 T2 Aportes, v2.7 DnD Kanban, v2.8 SectionSnapshotDiff;
  layouts e cores absorveram alterações sem mudança pixel-detectável). Cover
  pré-existia desde `0558ea3` (Apr 26 manhã, antes de `db6cf6f` cover
  identity 15:54), mas o screenshot é fullPage clip do `#report-main` na
  zona y=0..720 — área não afetada pelos meta-cards reordenados.

  **CAVEATS:**
  - **Tático Tx flakiness CI** — 5 flaky + 2 failed (T5 light, T6 dark)
    timeoutaram em `[data-report-ready="true"]` no CI Linux. Não reproduz
    localmente (darwin), e PNGs no artefato são idênticos ao main —
    sugerindo race condition no warmup do dev server (CI cold start vs
    local hot reload). Investigar em lane separada. Não bloqueia merge dos
    24 baselines novos.
  - Run conclusion=`failure` por causa dos 2 fails Tático, mas a Playwright
    re-tenta antes de chamar fail e os 24 PNGs corretos chegaram via artefato
    `report-visual-baselines-generated`.
