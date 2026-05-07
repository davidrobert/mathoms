---
id: ADR-155
type: adr
title: "`/dashboard` absorvido por `/plano` (Direção E consolidação)"
status: Decidido
phase: "Direção E · consolidação"
date: "2026-04-29"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 155"]
tags:
  - area/frontend
  - status/decidido
  - type/adr
size_lines: 88
---

# ADR-155 — `/dashboard` absorvido por `/plano` (Direção E consolidação)

**Status:** Decidido (Direção E · consolidação) • **Data:** 2026-04-29 •
**Conclui agenda da** [ADR-151](#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces)
(Direção E declarou "/dashboard será absorvido pelo /plano em onda
futura" — esta ADR cumpre).

**Contexto:** A Direção E original (Onda 4) tornou `/plano` um
"executive summary" com KPIs estratégicos + banner sugestões + Hero
IF + metas de suporte + decisões em vigor. O brainstorm declarou
**"/dashboard será absorvido pelo /plano em onda futura"** mas a onda
nunca aconteceu. `/dashboard` permaneceu como rota viva com 7
componentes próprios (KpiRow, ChartsGrid, AlertCard, HeaderActions,
BarChartCard, PieChartCard, ChartSkeleton + dashboardHelpers).

Análise pós-Direção E (2026-04-29 com user) considerou 3 alternativas:

- **(a) Manter os 3 (Plano + Dashboard + Ação)** — diferenciar por
  cadência (diário/mensal/diário) e verbo (estado/direção/execução).
  Trade-off: maior poder, mas usuário precisa "saber qual abrir".
- **(b) Manter 3 com ajustes** — variação de (a).
- **(c) Voltar para 2 (Plano absorve Dashboard)** — Direção E original.
  Trade-off: `/plano` fica gordo (estratégia + operacional do mês),
  mas é uma única "home" mental.

User escolheu **(c)** — fechamento absoluto da agenda da Direção E.

**Decisão:** `/dashboard` é absorvido por `/plano`. Componentes movem
de `frontend/src/app/(app)/dashboard/_components/` para
`frontend/src/app/(app)/plano/_components/_dashboard/` (sub-pasta
preservando agrupamento). `/plano` ganha 3 seções verticais (separadas
por `<SectionDivider/>`):

1. **Topo (estratégia/glance)**: PlanoKpiRow + SuggestionsBanner +
   Hero IF + SupportGoalsRow.
2. **Meio (mês corrente, ex-`/dashboard`)**: alertas + KpiRow
   operacional + ChartsGrid. Componentes idênticos ao
   `/dashboard` anterior — só mudaram de pasta.
3. **Base (plano de ação)**: DecisionsSection + UpcomingTasksWidget +
   LinkedTasksSection.

`/dashboard/page.tsx` vira redirect 308 para `/plano`. AppShell e
CommandMenuDialog removem entry "Dashboard" (LayoutDashboard icon
import retirado). Endpoint `/v1/dashboard` permanece intacto (agora
consumido pelo `/plano`).

**Consequências:**

- ✅ Mathoms agora tem **2 superfícies vivas**: `/plano` (home única)
  e `/acao` (superfície dinâmica). Mais fácil de explicar para
  usuário novo: "Plano é onde você lê; Ação é onde você faz".
- ✅ Direção E completa em main — agenda do brainstorm 2026-04-29
  (~/.claude/plans/quero-repensar-as-interfaces-mellow-nova.md)
  fechada 100%.
- ✅ `/plano` materializa modelo "Sua vida financeira em um lugar":
  estado patrimonial + estado operacional do mês + plano de ação
  numa única tela vertical scaneável.
- ⚠️ `/plano` fica longo (3 seções + ~12 blocos). Mitigado por
  `<SectionDivider/>` com headings uppercase (escaneável). Se virar
  ruído, futura onda pode introduzir collapsibles ou tabs internas.
- ⚠️ `frontend/tests/pages/dashboard.test.tsx` deletado (testava
  página inexistente). Componentes movidos para
  `plano/_components/_dashboard/` ficam sem cobertura de página
  específica — gap pré-existente que vira responsabilidade de
  `plano.test.tsx` (lane futura).
- ❌ Quem tinha bookmark de `/dashboard` precisa atualizar. Redirect
  308 (permanent) preserva deep-links durante janela transitória;
  não há sunset agendado para o redirect.

**Referências de código:**

- `frontend/src/app/(app)/plano/page.tsx` — reescrito com 3 seções +
  `useDashboardData` hook local consumindo `getDashboard`.
- `frontend/src/app/(app)/plano/_components/_dashboard/` — pasta nova
  com 8 componentes (`AlertCard`, `BarChartCard`, `ChartSkeleton`,
  `ChartsGrid`, `HeaderActions`, `KpiRow`, `PieChartCard`,
  `dashboardHelpers`) movidos via `git mv`.
- `frontend/src/app/(app)/dashboard/page.tsx` — redirect 308 via
  `redirect()` Server Component.
- `frontend/src/components/AppShell.tsx` — entry "Dashboard" removida
  do grupo "Fechamento do período"; `LayoutDashboard` import retirado.
- `frontend/src/components/command-palette/CommandMenuDialog.tsx` —
  entry "Dashboard" removida; tipo do icon trocado para `Target`.
- `frontend/src/types/report-analysis.ts` — comentários atualizados
  para refletir `/plano` como destino dos types `DashboardData` /
  `AporteItem` / `InvestimentoDeltaItem`.
