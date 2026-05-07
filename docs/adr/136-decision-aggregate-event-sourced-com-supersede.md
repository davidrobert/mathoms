---
id: ADR-136
type: adr
title: "`Decision` aggregate event-sourced com supersede chain"
status: Decidido
phase: "Sprint A7"
date: "2026-04-26"
relates_to: ["[[ADR-090]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 136"]
tags:
  - type/adr
  - status/decidido
size_lines: 119
---

# ADR-136 — `Decision` aggregate event-sourced com supersede chain

**Status:** Decidido (Sprint A7) • **Data:** 2026-04-26 • **Relaciona**
[ADR-090](#adr-090--decimal-para-valores-monetários),
[ADR-101](#adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e),
[ADR-115](#adr-115--domain-events-tipados-arquitetura-e-boundaries-a6eevents),
[ADR-134](#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend).

> **Nota (2026-05-06):** estendida por
> [ADR-179](#adr-179--decision-aggregate--extensão-de-schema-impact_1y10y-horizon-priority)
> (Sprint A10) — schema ganha `impact_1y_brl_cents`, `impact_10y_brl_cents`,
> `horizon`, `priority` via Alembic non-breaking. Aggregate event-sourced
> permanece; extensão é additive.

**Contexto:** `config/decisions.md` é um caderno editorial do cliente —
**não** ADRs arquiteturais. Contém 15 itens (D01..D15) com:

- Status que evolui no tempo (Pendente → Decidido → Executado).
- Supersede chain (D15 substitui D06 quando TRS muda de 4% → 5%).
- Valor envolvido em BRL (R$117.430 quitação financiamento, R$30k/mês
  meta IF, R$500/mês DCA crypto).
- Data de decisão e prazo de execução.

Hoje vive em markdown estático versionado em git. Três problemas:

1. **PII**: arquivo expõe valores reais em BRL — viola CLAUDE.md
   §Regras críticas (dados sensíveis em commits proibidos).
2. **Sem lifecycle**: status muda no markdown via edit manual; histórico
   se perde ou vira diff de git incompreensível para usuário não-dev.
3. **Mono-cliente**: arquivo serve apenas o workspace original do CLI.
   Multi-tenant exige entidade per-workspace.

Alternativas:

- **(a) CRUD puro `decisions(id, status, ...)` com UPDATE de status.**
  Perde audit trail. Não captura supersede chain naturalmente.
- **(b) Tabela `decisions` + `decision_status_changes` (changelog
  paralelo).** Funciona mas duplica modelos quando todo evento é
  basicamente uma transição.
- **(c) Aggregate event-sourced**: `decisions` (estado projetado) +
  `decision_events` (append-only log de eventos tipados). Audit trail
  nativo, supersede como tipo de evento, status como projeção.

**Decisão:** Adotar (c) **escopado a este aggregate apenas** —
não se torna convenção a propagar para outros aggregates do sistema. O
resto do app continua CRUD onde for adequado (alinhado com
[ADR-101](#adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e)).

Schema:

```sql
decisions (
  id UUID PK,
  workspace_id UUID FK NOT NULL,
  code TEXT NOT NULL,             -- "D01", "D15"
  title TEXT NOT NULL,
  rationale TEXT,
  amount_brl_cents BIGINT NULL,
  status TEXT NOT NULL,           -- enum: Pendente, Decidido, Executado, Descartado, Superseded
  supersedes_id UUID FK NULL,
  decided_at DATE NULL,
  executed_at DATE NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, code)
);

decision_events (
  id UUID PK,
  decision_id UUID FK NOT NULL,
  event_type TEXT NOT NULL,       -- Created, StatusChanged, Superseded, Executed, Updated
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor TEXT NOT NULL,            -- "system:migrator", "user:<id>", "agent:<name>"
  payload JSONB NOT NULL          -- evento tipado (DTO Pydantic serializado)
);
```

Use cases em `backend/app/application/decisions/`:

- `CreateDecision` — emite `DecisionCreatedEvent`.
- `UpdateDecision` — emite `DecisionUpdatedEvent` com diff.
- `MarkDecisionExecuted` — emite `DecisionExecutedEvent` + atualiza
  `executed_at`.
- `SupersedeDecision(new_id, old_id)` — emite
  `DecisionSupersededEvent`; status do antigo vira `Superseded`,
  `supersedes_id` do novo aponta para o antigo.

Endpoints REST: `GET/POST /api/v1/workspaces/{id}/decisions`,
`GET/PATCH /api/v1/workspaces/{id}/decisions/{decision_id}`,
`POST /api/v1/workspaces/{id}/decisions/{decision_id}/execute`. Todos
com `response_model` explícito ([ADR-109](#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a)).

Eventos do aggregate **não** entram em
[ADR-115](#adr-115--domain-events-tipados-arquitetura-e-boundaries-a6eevents) (cross-aggregate
events) — são internos. Se outro aggregate precisar reagir
(`Notification` quando decisão executada >R$50k), aí sim emite domain
event tipado pelo dispatcher.

Migrator one-shot: `dev/migrate_decisions_to_db.py` parseia
`config/decisions.md`, cria 15 rows + eventos `Created` no workspace
alvo. Idempotente. **Descartável** — não generalizar.

Money em `amount_brl_cents` (BIGINT) — [ADR-090](#adr-090--decimal-para-valores-monetários).

**Consequências:**
- ✅ Audit trail nativo: timeline de decisão é select linear em
  `decision_events`.
- ✅ Supersede chain explícita; UI renderiza "supersedes D06" como
  link.
- ✅ `decisions.md` removido — resolve dívida PII.
- ⚠️ Padrão event-sourced é diferente do resto do app — requer
  documentação extra para agentes/devs. Aceito porque o domínio do
  aggregate (decisões com lifecycle) justifica.
- ⚠️ Migrator é frágil (parser markdown). Aceito porque roda uma vez
  e depois morre.
- ❌ Eventos não compõem com event bus geral (ADR-115). Decisão
  consciente — escopo do aggregate; se virar cross-aggregate, refatora.
