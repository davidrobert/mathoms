---
id: F11.2
type: lane
title: "Hierarquia de números"
sprint: F11
status: shipped
priority: P1
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f11
  - status/shipped
  - priority/p1
---


# F11.2 — Hierarquia de números


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.2a | **Auditoria visual:** mesmas regras de `format.ts` aplicadas em Dashboard, Transactions, Report React: alinhamento decimal, `tabular-nums`, escala de eixos Recharts, legenda com unidade. | P1 | 8h | ✅ Sprint B+C: Dashboard (eixos/tooltips); Transactions (data/valor/cabeçalho/paginação); hero do relatório nativo; KPICard/`MonetaryValue` já cobertos — revisão fina por seção/card se necessário |
| F11.2b | **Prioridade semântica:** KPI primário vs secundário (peso tipográfico / posição); valores derivados claramente subordinados (ex.: variação % sob o principal). | P1 | 4h | ✅ `KPICard` `emphasis` + hero do relatório (título vs período); delta menor no modo secundário |
| F11.2c | **Teste de regressão visual** (Playwright ou checklist manual) para dark/light e print. Entregue em 2026-04-25 como item 3 da lane [`report-a11y-finalize`](#lanes-abertas-agora--pickup-table) — spec [`sections.snapshots.visual.spec.ts`](../frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts) + job CI `frontend-visual` opt-in + ops doc [REPORT_VISUAL_SNAPSHOTS.md](REPORT_VISUAL_SNAPSHOTS.md). Baselines Linux aguardam trigger manual em CI. | P2 | 3h | ✅ 2026-04-25 |
