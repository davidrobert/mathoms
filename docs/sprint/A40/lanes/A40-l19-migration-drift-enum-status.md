---
id: A40.l19
type: lane
title: "Drift de enum de status: 4 valores existem em Python e não no tipo do DB"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l19-migration-drift-enum-status
adrs:
  - "[[ADR-357]]"
  - "[[ADR-359]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/backend
  - area/db
---

# A40.l19 — `migration-drift-enum-status`

> Onda 3 da A40 (§Frente 4 de [[PLAN-report-trust]]). **PR próprio** (migration não
> mistura com feature). P1 de execução, mas **gate de deploy** do cutover
> Postgres.

> **Segundo consumidor (2026-08-03, [[ADR-359]]):** além da [[ADR-357]] §7, o
> `resuming` ausente do tipo do DB bloqueia a varredura de órfão da [[A40.l27]] —
> lá o `resuming` entra em **predicado de query**, e um órfão nesse estado é hoje o
> único que nenhuma superfície mata. Se esta lane escorregar, **dois** consumidores
> param, e a l27 entrega parcial declarando o item 1 como não-entregue.

## Problema

A migration inicial criou os enums com menos valores do que o Python declara
hoje, e não há nenhum `ALTER TYPE` para os que entraram depois:

| tipo | criado na migration | falta no DB |
| --- | --- | --- |
| `pipelinestagestatus` | `pending, running, completed, failed, skipped` | `skipped_free_tier`, `needs_review` |
| `pipelinerunstatus` | `pending, running, completed, partial_failure, failed, cancelled` | `needs_review`, `resuming` |

Funciona porque dev/prod atual é SQLite e o default de SQLAlchemy 2.x é
`create_constraint=False`. Em Postgres, `INSERT 'needs_review'` em
`pipeline_stage_logs.status` **explode** — e esse caminho **já está vivo**
(`_record_stage_needs_review`, alimentado por [[ADR-272]]/E3). Ou seja: o drift
não é teórico nem futuro; é uma quebra armada esperando o cutover.

Os únicos `ALTER TYPE` do repo são para `documenttype` (2 migrations) — há
padrão de forma a seguir, guardado por dialeto e no-op em SQLite.

## Decisão

Uma migration com os **5** valores: os 4 em drift + `degraded` da [[ADR-357]].
Padrão `ALTER TYPE ... ADD VALUE IF NOT EXISTS`, guardado por dialeto.

Pago agora, no nosso tempo, em vez de descoberto no cutover — a janela é livre
porque Postgres ainda não existe em produção.

## Critério de aceite

- `pytestmark = pytest.mark.migration` (senão PR sem
  `backend/alembic/versions/**` skipa via `-m "not migration"`).
- upgrade/downgrade verdes em SQLite (no-op assertado).
- Asserção de que o `ALTER TYPE` é guardado por dialeto.
- Enumeração cruzada: todo membro dos enums Python existe no tipo do DB. Gate
  estático que falha se alguém adicionar valor ao Python sem migration.
