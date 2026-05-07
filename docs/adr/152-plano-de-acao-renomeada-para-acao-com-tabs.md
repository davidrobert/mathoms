---
id: ADR-152
type: adr
title: "`/plano-de-acao` renomeada para `/acao` com tabs (Direção E · Onda 6)"
status: Decidido
phase: "Direção E · Onda 6"
date: "2026-04-29"
relates_to: ["[[ADR-151]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 152"]
tags:
  - type/adr
  - status/decidido
size_lines: 89
---

# ADR-152 — `/plano-de-acao` renomeada para `/acao` com tabs (Direção E · Onda 6)

**Status:** Decidido (Direção E · Onda 6) • **Data:** 2026-04-29 •
**Relaciona** [ADR-151](#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces)
(remoção do Modo Tático),
[ADR-074](#adr-074--tasks-como-entidade-de-1ª-classe-fora-do-relatório)
(Task aggregate),
[ADR-136](#adr-136--decision-aggregate-event-sourced-com-supersede-chain)
(Decision aggregate).

**Contexto:** A Direção E (refinada com product-designer) consolida
em `/acao` toda a interação ativa do usuário: **Inbox de sugestões**
(da Onda 5), **Tarefas** (Task aggregate, ADR-074), **Timeline**
(próximos 15 dias), **Notas livres** (workspace_notes da Onda 1).

A rota anterior `/plano-de-acao` carregava só Tasks e gerava confusão
nominal — havia 4 entidades competindo pelo nome "plano de ação"
(`/plano-de-acao`, S10 do relatório com Decisions, Modo Tático T3
Kanban, label "Plano de Ação" no nav). Direção E reduziu para 2
modelos claros: **Decisions vivem em `/plano`** (gestão de plano),
**execução vive em `/acao`**.

**Decisão:**

1. **Renomear rota**: `/plano-de-acao` → `/acao`. Sub-rota
   `/plano-de-acao/sugestoes` → `/acao/sugestoes`.
2. **`/plano-de-acao` (e sub-rota) viram redirects 308** (permanent)
   para preservar deep-links existentes em e-mails, marcadores e
   commits passados.
3. **`/acao/page.tsx` orquestra 4 tabs** (Tabs do shadcn/base-ui):
   - **Inbox** — placeholder ensinante até Onda 5 ligar Suggestion
     full-stack (aggregate novo).
   - **Tarefas** — conteúdo migrado de `/plano-de-acao/page.tsx`
     atual: views por prioridade/prazo/categoria, drawer, form dialog,
     transições in_progress/done/reopen/cancel.
   - **Timeline** — placeholder até definir fonte estável fora do
     contexto de relatório (`dashboard.proximos_15d` está no snapshot,
     mas para `/acao` precisa endpoint dedicado).
   - **Notas** — placeholder até Onda 1 entregar `workspace_notes`
     (substituindo `report_notes` deprecated em ADR-151).
4. **`ActionStatusBar`** no topo agrega contadores: sugestões
   pendentes, tarefas próximos 7 dias, decisões a executar
   (`status === "Decidido"`).
5. **Default tab**: Tarefas (estado atual). Quando Onda 5 ligar
   Suggestions, alternar para Inbox quando houver pendentes (designer
   recommendation: "força o ritual").
6. **Label de navegação**: "Plano de Ação" → "Ação" no `AppShell`
   sidebar e `CommandMenuDialog`. Mais curto, distinto de `/plano`.

**Consequências:**

- ✅ Direção E materialmente visível: `/plano` (one-page executivo,
  Onda 4) + `/acao` (superfície dinâmica, esta) + relatório (foto +
  análise) — 3 superfícies com mandatos distintos.
- ✅ Banner de sugestões em `/plano` (Onda 4) agora aponta para algo
  real (`/acao`); ritual sugestão→aceitar→Decision/Task começa a
  fazer sentido visualmente.
- ✅ Componentes existentes preservados: `TaskCard`, `TaskDrawer`,
  `TaskFormDialog`, `useUpcomingTasks` reutilizados sem mudança.
  `TasksTab` é refactor interno (lógica idêntica em sub-componentes
  menores).
- ⚠️ Rota antiga retorna 308 (não 301) por limitação do
  `redirect()` do Next.js Server Components. Equivalente semântico
  para SEO; cache CDN respeita.
- ⚠️ Inbox, Timeline e Notas ficam como **placeholders ensinantes**
  até Ondas 5 e 1. Empty state precisa explicar — não pode parecer
  "feature quebrada".
- ❌ Quem fizer bookmark de `/plano-de-acao?tab=...` perde state da
  query string no redirect. Aceitável; deep-link com tab vai depender
  de query/hash em `/acao` quando produto pedir.

**Referências de código:**

- `frontend/src/app/(app)/acao/page.tsx` — orchestrator com tabs
  (74 LOC, baixo de 60 alvo após split em sub-componentes).
- `frontend/src/app/(app)/acao/_components/`:
  - `TasksTab.tsx` — conteúdo migrado, dividido em sub-componentes
    (TasksHeader, ViewToggle, TasksGroups, helpers de groupBy).
  - `InboxTab.tsx`, `TimelineTab.tsx`, `NotasTab.tsx` — empty states.
  - `ActionStatusBar.tsx` — chips de contadores.
- `frontend/src/app/(app)/acao/sugestoes/page.tsx` — movida de
  `/plano-de-acao/sugestoes` (git mv).
- `frontend/src/app/(app)/plano-de-acao/page.tsx` — redirect 308.
- `frontend/src/app/(app)/plano-de-acao/sugestoes/page.tsx` —
  redirect 308.
- Links atualizados em: `SuggestionsBanner`, `LinkedTasksSection`,
  `AppShell`, `CommandMenuDialog`, `UpcomingTasksWidget`.
