---
id: CHG-2026-04-29-A10-DIRE-O-E-DASHBOARD-A
type: changelog-entry
date: "2026-04-29"
sprint: A10
adrs: ["[[ADR-155]]"]
summary: |
  Direção E — `/dashboard` absorvido por `/plano` (consolidação, 2026-04-29). - **Direção E — `/dashboard` absorvido por `/plano` (consolidação, 2026-04-29):** Cumpre a agenda da Direção E original que declarou "/dashboard será absorvido
tags:
  - type/changelog-entry
  - sprint/a10
---


# Direção E — `/dashboard` absorvido por `/plano` (consolidação, 2026-04-29)

- **Direção E — `/dashboard` absorvido por `/plano` (consolidação, 2026-04-29):**

  Cumpre a agenda da Direção E original que declarou "/dashboard será
  absorvido pelo /plano em onda futura"
  ([ADR-155](../../../DECISIONS.md#adr-155--dashboard-absorvido-por-plano-direção-e-consolidação)).
  Mathoms agora tem **2 superfícies vivas**: `/plano` (home única —
  estratégia + operacional do mês + plano de ação) e `/acao`
  (superfície dinâmica de execução). Modelo mental do usuário: "Plano
  é onde você lê; Ação é onde você faz".

  **Frontend:**
  - 8 componentes movidos via `git mv` de
    `frontend/src/app/(app)/dashboard/_components/` para
    `frontend/src/app/(app)/plano/_components/_dashboard/`
    (AlertCard, BarChartCard, ChartSkeleton, ChartsGrid,
    HeaderActions, KpiRow, PieChartCard, dashboardHelpers).
  - `frontend/src/app/(app)/plano/page.tsx` reescrito em 3 seções
    verticais separadas por `<SectionDivider/>`: (1) topo
    estratégico (PlanoKpiRow + SuggestionsBanner + Hero IF +
    SupportGoalsRow); (2) "Mês corrente" (alertas + KpiRow
    operacional + ChartsGrid); (3) "Plano de Ação" (DecisionsSection
    + UpcomingTasksWidget + LinkedTasksSection).
  - Hook local `useDashboardData` em `plano/page.tsx` consume
    `getDashboard` (endpoint `/v1/dashboard` permanece intacto).
  - `frontend/src/app/(app)/dashboard/page.tsx` vira **redirect 308**
    via `redirect()` Server Component.
  - `frontend/src/components/AppShell.tsx`: entry "Dashboard" removida
    do grupo "Fechamento do período"; `LayoutDashboard` import
    retirado.
  - `frontend/src/components/command-palette/CommandMenuDialog.tsx`:
    entry "Dashboard" removida; tipo do icon trocado para `Target`.
  - `frontend/src/types/report-analysis.ts`: comentários atualizados
    para refletir `/plano` como destino.
  - `frontend/tests/pages/dashboard.test.tsx`: **deletado** (testava
    página que não existe mais; componentes movidos sem cobertura
    específica — gap futuro vira `plano.test.tsx`).

  **Backend:** sem mudanças (endpoint `/v1/dashboard` permanece
  intacto, agora consumido pelo `/plano`).
