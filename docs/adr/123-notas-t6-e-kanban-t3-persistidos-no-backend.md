---
id: ADR-123
type: adr
title: "Notas (T6) e Kanban (T3) persistidos no backend"
status: Decidido
phase: "Fase 0"
date: "2026-04-23"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-154]]", "[[ADR-168]]"]
aliases: ["ADR 123"]
tags:
  - area/backend
  - area/multitenancy
  - area/report
  - status/decidido
  - type/adr
size_lines: 43
---

# ADR-123 — Notas (T6) e Kanban (T3) persistidos no backend

> **Nota (2026-04-29):** parcialmente superseded por
> [ADR-151](#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces)
> — Modo Tático (T3 Kanban + T6 Notas) foi removido do relatório.
> Tabelas `kanban_items` e `report_notes` permanecem no DB durante a
> janela transitória; serão migradas para `tasks` + `workspace_notes`
> na Onda 1 da Direção E. Endpoints REST permanecem disponíveis sem
> consumer no frontend.

**Status:** Decidido (Fase 0) • **Data:** 2026-04-23

**Contexto:** Relatório premium tem dois componentes editáveis pelo usuário:
`NotasCard` (textarea de anotações por relatório) e `Kanban` (tarefas
arrastáveis). Discovery propôs localStorage (compatível com ADR-111
stateless). Usuário decidiu **persistir no backend** — permite
multi-dispositivo, multi-usuário e exportação.

**Decisão:** Duas tabelas novas + 4 endpoints REST:

- `report_notes` `{id, workspace_id, report_id, author_user_id, content,
  updated_at}` — 1:1 com report (unique em `(workspace_id, report_id)`).
- `kanban_items` `{id, workspace_id, report_id, titulo, prioridade,
  prazo_iso, coluna, ordem, categoria, essencial, updated_at}` — 1:N.
- Endpoints: `GET/PUT /v1/reports/{id}/notes`,
  `GET/POST/PATCH/DELETE /v1/reports/{id}/kanban[/{item_id}]`. `response_model`
  explícito (ADR-109). OpenAPI snapshot atualizado via `make update-openapi-snapshot`.
- Debounce autosave 500ms no frontend → PUT idempotente.
- Sem collaboration em tempo real (last-write-wins). Conflito raro:
  usuário único por workspace no near term.

**Consequências:**
- ✅ Multi-dispositivo + exportação viáveis.
- ✅ Continua stateless (ADR-111) — estado vive no DB, não em memória.
- ⚠️ Fase 8 (tactical sections) cresce — não é mais localStorage puro.
  Estimativa sobe ~1 dia.
- ⚠️ Migração Alembic nova; cuidar de ordem em branch compartilhada.
- ❌ Latência de save perceptível em conexão lenta — mitigado por
  optimistic UI + indicador `.notas-save-dot`.

Relaciona-se a: ADR-109 (response_model), ADR-111 (stateless).
