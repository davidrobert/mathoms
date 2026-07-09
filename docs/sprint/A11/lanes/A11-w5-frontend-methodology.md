---
id: A11.w5
type: lane
title: "Frontend + Methodology (5 tasks, paralelo W6)"
sprint: A11
status: shipped
aliases: ["A11.W5"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a11
  - status/shipped
---


# A11.w5 — Frontend + Methodology (5 tasks, paralelo W6)

> Migrada de tabela em `## Sprint A11` do BACKLOG (F4.A.followup, ADR-182).

## Contexto da tabela original

- **Onda:** 5 (10d)
- **Depende de:** W1 ✅ (parcial)
- **Plano:** [PLAN §W5](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-5--frontend--methodology-sprint-4-10-dias-dev)

## Status

**Pickup real — 5 tasks com escopo reduzido** (re-verificação factual
2026-07-08, spike W5 pós-A33 — detalhe por task em
[PLAN §Wave 5](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-5--frontend--methodology-sprint-4-10-dias-dev)):

- W5-T01 (a11y) ◐ parcial — resta `scope="col"` (22 arquivos c/ `<th>`), `role="progressbar"` + primitivo `<ProgressBar/>`, `prefers-reduced-motion` global; gate axe (critical+serious) já roda em @critical
- W5-T02 (Recharts → Chart.js residual S1) ☐ válida — 2 charts (`PatrimonioDoughnutChart`, `WaterfallIfChart`); primitivos prontos; fechamento = emenda datada na [[ADR-139]]
- W5-T03 (MonetaryValue migration) ☐ válida — 13 call-sites monetários com `toLocaleString` direto + helpers locais duplicados
- W5-T04 (ADR-161 enrichment) ◐ parcial — sub-PR #5 ✅ via W1-T02; #2 obsoleto ([[ADR-239]]/[[ADR-240]]); #1/#3/#4 válidos (produtores E5 ausentes; regras dormentes)
- W5-T05 (Goal IF v2) ◐ parcial — numerador `investivel_efetivo` + toggle `imoveis_no_if` ✅; resta `if_meta_liquida` + emissão v2 ([[ADR-140]] `Roadmap`)

## Sub-tracks ativos

- **S9-Expansion** ✅ **consumed 2026-05-12** — track [s9-riscos-expansion](../tracks/s9-riscos-expansion.md), ADR canônica [[ADR-192]] `Decidido (Sprint A11.W5)`:
  - T01 ✅ ([#212](https://github.com/davidrobert/mathoms/pull/212), 2026-05-11) — hotfix narrativa
  - T02 ✅ ([#219](https://github.com/davidrobert/mathoms/pull/219), commit `e1e0ffd`) — Protection aggregate + ProtectionBundle skeleton + flip ADR-192
  - T03 ✅ ([#228](https://github.com/davidrobert/mathoms/pull/228), commit `ac55082`) — 4 calculators + auto-inferência
  - T04 ✅ ([#227](https://github.com/davidrobert/mathoms/pull/227), commit `432f96d`) — 4 cards UI + bubble re-enquadrado · follow-up visual baselines [#229](https://github.com/davidrobert/mathoms/pull/229)
  - T05 ✅ ([#230](https://github.com/davidrobert/mathoms/pull/230), commit `a7874ed`) — UI `/protecao` + form cadastro + smoke E2E
  - T06 ✅ (este PR) — goldens E5 verificados (zero drift); fecha o track

## Fechamento (closure A11, 2026-07-08)

Residual executável entregue na sessão de closure: **W5-T01** a11y
([#882](https://github.com/davidrobert/mathoms/pull/882)) · **W5-T02**
charts + emenda [[ADR-139]] ([#883](https://github.com/davidrobert/mathoms/pull/883))
· **W5-T03** monetário ([#884](https://github.com/davidrobert/mathoms/pull/884)).
W5-T04 #1/#3/#4 e W5-T05 saem da sprint como **backlog candidates**
(emenda [[ADR-228]]; track `docs/sprint/W5/tracks/w5t05-goal-if-v2.md`
preservado).
