---
id: ADR-151
type: adr
title: "Remoção do Modo Tático do relatório (Direção E do redesign de interfaces)"
status: Decidido
phase: "Direção E · Onda 3"
date: "2026-04-29"
relates_to: []
supersedes: ["[[ADR-117]]"]
superseded_by: []
aliases: ["ADR 151"]
tags:
  - type/adr
  - status/decidido
size_lines: 92
---

# ADR-151 — Remoção do Modo Tático do relatório (Direção E do redesign de interfaces)

**Status:** Decidido (Direção E · Onda 3) • **Data:** 2026-04-29 •
**Supersedes** parcial [ADR-117](#adr-117--report-premium-ui-baseline-paridade-com-exemplo_de_relatoriohtml)
(Modo Tático como dashboard operacional do relatório),
[ADR-123](#adr-123--notas-t6-e-kanban-t3-persistidos-no-backend)
(persistência server-side do Kanban T3 e Notas T6 no contexto do relatório).

**Contexto:** O relatório nativo React tinha 3 modos (Estratégico,
Tático, USA). O Modo Tático (T1–T6) misturava conteúdo de leitura
(snapshot patrimonial) com **estado mutável editável in-loco** —
Kanban T3 (KanbanItem persisted via ADR-123) e Notas T6 (report_notes
persisted via ADR-123) com autosave 500ms. Esse acoplamento gerava
três tensões:

1. **Relatório quer ser fotografia mensal** — o PDF exportado via
   Playwright congelava conteúdo que era para ser vivo (Kanban editado
   após geração não refletia no PDF anterior).
2. **Mesmo dado em N lugares** — tarefas em `/plano-de-acao` (Tasks),
   `/plano` (LinkedTasksSection IF), `/dashboard` (UpcomingTasksWidget),
   T3 do relatório (KanbanItem) — 4 modelos competindo pelo nome "plano
   de ação", sem clareza para o usuário.
3. **Confusão entre Decision (ADR-136), Task (ADR-074) e KanbanItem
   (ADR-123)** — três aggregates para "coisa pra fazer", os dois últimos
   quase idênticos.

**Decisão:** Remover o Modo Tático do relatório. Mover `plano_de_acao`
(seção que renderiza Decisions D01–D15) para `estrategico:` no YAML.
Componentes de Modo Tático (`TaticoSections.tsx`, `aportesAdapter.ts`,
testes táticos) deletados. Tipo `ReportMode` reduzido para
`'estrategico' | 'usa'`. Banco de dados `kanban_items` e `report_notes`
permanecem por enquanto (migração para `tasks` + `workspace_notes` será
Onda 1 da Direção E).

**Consequências:**

- ✅ Relatório vira artefato coerente — só leitura. PDF congela snapshot;
  estado mutável vive em superfícies dedicadas (`/plano`, `/acao`).
- ✅ `MIGRATED_SECTIONS` e switch `MigratedSection` no `ReportShell`
  ficam mais simples (8 seções estratégicas + 4 USA + plano_de_acao + 5
  apêndices, vs 22 seções no estado anterior).
- ✅ Codegen `dev/codegen_report_layout.py` mais limpo: tipos `Tatico`,
  `tatico` em `NavigationSpec` e `ReportLayout` removidos.
- ✅ Onda 2 já entregue (UI de Decisions em `/plano`, branch
  `agent/decisions-ui-plano/20260428-1654`) **não precisa ser refeita**
  — designer recomendou Decisions ficarem em `/plano` (gestão de plano);
  só Sugestões (Onda 5 futura) viverão em `/acao`.
- ⚠️ Tabelas `kanban_items` e `report_notes` ficam órfãs até Onda 1
  (migração). Endpoints de Kanban/Notes permanecem disponíveis — sem
  consumer no frontend, mas o backend não foi tocado nesta onda.
- ⚠️ Workspace piloto "Allen" perde temporariamente acesso ao Kanban
  do relatório. Itens existentes em `kanban_items` permanecem no DB e
  serão migrados para `tasks` na Onda 1.
- ⚠️ Snapshots visuais do Modo Tático (T1-T6 light/dark) em
  `tests/e2e/reports/__snapshots__/sections.snapshots.visual.spec.ts/`
  ficam órfãos — limpar manualmente em CI Linux na próxima refresh.
- ❌ Quem buscava "minhas tarefas no relatório" terá que ir a
  `/plano-de-acao` (Tasks) ou `/plano` (Decisions) até Onda 6 fundir
  ambos em `/acao`.

**Modelos de domínio na Direção E (visão consolidada):**

| Aggregate | Onde vive | Status |
|---|---|---|
| `Decision` (ADR-136) | `/plano` — UI de gestão (Onda 2 ✅) + apêndice "em vigor" no relatório | Ativo |
| `Task` (ADR-074) | `/plano-de-acao` (Onda 6 → renomeia para `/acao` com tabs) | Ativo |
| `KanbanItem` (ADR-123) | Órfão — tabela viva, sem consumer, migra em Onda 1 | Deprecated |
| `ReportNotes` (ADR-123) | Órfão — tabela viva, sem consumer, migra em Onda 1 | Deprecated |
| `Suggestion` (novo) | Onda 5 — gerada pelo pipeline E5, lida pelo relatório (`<SuggestionCallout/>`) e por `/acao` (`<SuggestionCard/>`) | Roadmap |

**Referências de código:**

- `config/report_layout.yaml` — bloco `tatico:` removido; `nav.tatico`
  removido; `plano_de_acao` movido para `estrategico.sections` com
  título "Plano de Ação — Decisões em Vigor".
- `dev/codegen_report_layout.py` — tipo `Tatico`, `NavigationSpec.tatico`
  e referências a `LAYOUT.tatico` removidos. ReportMode reduzido.
- `frontend/src/components/report/ReportShell.tsx` — imports T1-T6
  removidos, `MIGRATED_SECTIONS` sem T1-T6, `selectSections`/
  `buildNavGroups`/`MigratedSection` simplificados.
- `frontend/src/components/report/ReportModeContext.tsx` — `VALID_MODES`
  só `estrategico` + `usa`.
- `frontend/src/components/report/shell/ModeToggle.tsx`,
  `ReportActions.tsx`, `ReportTopNav.tsx` — labels e listas atualizadas.
- `frontend/src/components/report/sections/TaticoSections.tsx` —
  **deletado** (494 LOC).
- `frontend/src/components/report/utils/aportesAdapter.ts` —
  **deletado** (consumer único era T2).
- `frontend/tests/components/report/taticoSections.test.tsx` —
  **deletado**.
