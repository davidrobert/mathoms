---
id: CHG-2026-04-29-A10-DIRE-O-E-ONDA-4-ONDA
type: changelog-entry
date: "2026-04-29"
sprint: A10
adrs: ["[[ADR-152]]"]
summary: |
  Direção E — Onda 4 + Onda 6: `/plano` executive + `/acao` consolidada (2026-04-29). - **Direção E — Onda 4 + Onda 6: `/plano` executive + `/acao` consolidada (2026-04-29):** **Onda 4 entregue (`/plano` executive summary):** novos componentes em
tags:
  - type/changelog-entry
  - sprint/a10
---


# Direção E — Onda 4 + Onda 6: `/plano` executive + `/acao` consolidada (2026-04-29)

- **Direção E — Onda 4 + Onda 6: `/plano` executive + `/acao` consolidada (2026-04-29):**

  **Onda 4 entregue (`/plano` executive summary):** novos componentes
  em `frontend/src/app/(app)/plano/_components/`: `PlanoKpiRow` (3
  KPIs no topo: patrimônio · IF % · aporte alvo), `SuggestionsBanner`
  (visível só se há sugestões pendentes; severidade info/warning),
  `useSuggestionsCount` (stub determinístico até Onda 5). Refactor
  interno em `usePlanoOverview` expõe `patrimonio` independente de
  `IFProgress` e elimina chamada duplicada a `listReports`.

  **Onda 6 entregue (rota `/acao` com tabs,
  [ADR-152](DECISIONS.md#adr-152--plano-de-acao-renomeada-para-acao-com-tabs-direção-e--onda-6)):**
  `/plano-de-acao` → `/acao` com 4 tabs (Inbox · Tarefas · Timeline ·
  Notas) e `ActionStatusBar` no topo agregando contadores (sugestões
  pendentes · tarefas próximos 7 dias · decisões a executar).
  Conteúdo de Tarefas migrado de `/plano-de-acao/page.tsx` (332 LOC
  monolítico) para `TasksTab.tsx` decomposto em sub-componentes
  (TasksHeader, ViewToggle, TasksGroups, helpers de groupBy). Inbox,
  Timeline, Notas ficam como **placeholders ensinantes** até Ondas 5
  e 1 ligarem o backend (Suggestion aggregate e workspace_notes).
  `/plano-de-acao` (e `/sugestoes`) viram redirects 308. Links
  atualizados em `SuggestionsBanner`, `LinkedTasksSection`, `AppShell`
  (label "Plano de Ação" → "Ação"), `CommandMenuDialog`,
  `UpcomingTasksWidget`. Sub-rota `sugestoes` movida com `git mv`.
