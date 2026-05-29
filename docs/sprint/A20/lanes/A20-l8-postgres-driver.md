---
id: A20.l8
type: lane
title: "Docker dev↔prod parity — L8 Postgres driver (psycopg2 → psycopg v3 swap)"
sprint: A20
status: shipped
priority: P1
branch_slug: a20-l8-postgres-driver
depends_on:
  - "[[A20.l1]]"
parallel_with:
  - "[[A20.l4]]"
  - "[[A20.l7]]"
adrs_canonical:
  - "[[ADR-253]]"
tags:
  - type/lane
  - sprint/a20
  - status/shipped
  - priority/p1
  - area/infra
  - area/db
  - area/devops
---

# A20.L8 — Postgres driver (psycopg2 → psycopg v3 swap)

> **Onda B** em [[MOC-sprint-a20]] — **obrigatória** (gap 1 do `senior-cto`).
> Resolve **P1.2** (driver legado `psycopg2-binary` em modo manutenção +
> `libpq5` apt dep bloqueavam enxugar runtime).

## Resumo

> ⚠️ **Pivot de escopo (co-design `data-engineer`, 2026-05-29).** A premissa
> original ("asyncpg-only com sync wrapper") era **factualmente errada**: o
> sync engine não serve só Alembic/healthcheck — ele drivea **44 arquivos** do
> task layer Celery (workers prefork síncronos). E Alembic **já roda async**
> (asyncpg em `env.py`). asyncpg-only exigiria reescrever 44 callsites para
> async (event-loop por-task em prefork = território de bug). Decisão invertida
> para **swap de driver legado**, detalhada em [[ADR-253]].

`psycopg2-binary` (sync engine) está em **modo manutenção**; psycopg v3 é a
linha ativa do mesmo autor. O swap **`psycopg2-binary` → `psycopg[binary]` v3**
elimina o driver legado, remove `libpq5`/`libpq-dev` (psycopg v3 binary embarca
libpq no wheel; asyncpg não linka libpq de sistema) e **preserva a arquitetura
de dois engines** (asyncpg async para FastAPI+Alembic; psycopg v3 sync para
Celery). Risco baixíssimo: não toca os 44 callsites, muda só a string de
conexão + 1 linha de requirements.

## Escopo IN (entregue)

- [[ADR-253]] reescrita e promovida a **Decidido** — driver final
  `psycopg[binary]` v3 (swap), dois engines mantidos.
- `backend/requirements.in`: `psycopg2-binary>=2.9` → `psycopg[binary]>=3.2`.
- `backend/app/core/config.py`: `sync_database_url` emite
  `postgresql+psycopg://` **explícito** (sem o driver explícito o SQLAlchemy
  cairia no default psycopg2, removido nesta lane).
- `Dockerfile`: builder remove `libpq-dev`; runtime remove `libpq5`.
- `requirements.lock` regenerado (container amd64): `psycopg==3.3.4` +
  `psycopg-binary`; `psycopg2` count = 0; asyncpg retido.
- 2 testes unitários novos em `test_config_prod_gates.py` (driver explícito).
- Runbook `python_dependencies.md` atualizado (valida `psycopg`, sem `libpq-dev`).

## Escopo OUT

- **Consolidação real em 1 driver** (migração async do task layer Celery) —
  fica para lane futura (A22+) com ADR e gate próprios.
- Migrar para `sqlmodel` ou outro ORM — non-goal.
- Substituir Alembic — non-goal (já é asyncpg, intocado).

## Pré-requisitos

- [[ADR-253]] — reescrita + Decidido. ✔
- [[A20.l10]] mergeada (lockfile combinado existe). ✔
- [[A20.l1]] — Dockerfile multi-stage existe; runtime stage perde `libpq5`. ✔

## Critério de aceite

1. `requirements.lock` **não contém** `psycopg2-binary` nem `psycopg2` —
   ✔ (regen verde, count = 0).
2. Stage `runtime` do Dockerfile **não instala** `libpq5` via apt — ✔
   (`docker run --rm --entrypoint dpkg mathoms-backend:l8test -l libpq5`
   retorna exit 1 / "no packages found").
3. Suíte completa verde — ✔ (`pytest backend/tests -q`: 2535 passed, 4 skipped).
4. **Smoke de paridade de driver** (ajustado do "p95 sob mudança de paradigma"
   — o paradigma async **não muda** neste swap). Round-trip JSONB +
   `timestamptz` na integração Postgres-real (CI) confirma paridade
   psycopg2→psycopg3.
5. `alembic upgrade head` fresh funciona — ✔ (Alembic é asyncpg, intocado).

## Definition of Done

- [x] PR mergeado em `main` com CI verde.
- [x] [[ADR-253]] promovida a `Decidido (A20.L8)`.
- [x] `psycopg2-binary` removido de `requirements.in`/`.lock`.
- [x] Image `runtime` sem `libpq5` (validado via `dpkg -l` exit 1).
- [x] Suíte local + build de imagem verdes.
- [x] [CHANGELOG](../../../CHANGELOG.md) entry registrada.

## Status de entrega

- **Pivot validado:** review blocking `data-engineer` derrubou a premissa
  asyncpg-only (44 callsites Celery + Alembic-já-async). Decisão final:
  swap psycopg2→psycopg3, dois engines. Ver [[ADR-253]] §"Correção de premissa".
- **Swap aplicado e verificado empiricamente:**
  - `requirements.lock` regenerado em container linux/amd64 —
    `psycopg==3.3.4` + `psycopg-binary`; `psycopg2` count = 0; asyncpg retido.
  - Imagem `mathoms-backend:l8test` builda exit 0 **sem `libpq-dev`** —
    confirma libpq embarcado no wheel binary.
  - `libpq5` ausente do runtime (`dpkg -l libpq5` exit 1).
  - `import psycopg` (3.3.4) + `import asyncpg` (0.31.0) OK na imagem.
  - 2 testes unitários novos verdes; suíte: 2535 passed / 4 skipped.
- **Débito remanescente (fora de escopo A20):** consolidação async do task
  layer Celery em 1 driver — lane A22+ com ADR própria.

## Riscos top 3 (mitigados)

1. **Behavior diff psycopg2→psycopg3** (timezone/timestamp/JSONB/NULL) —
   mitigado por round-trip JSONB + `timestamptz` na integração Postgres-real
   (CI). Baixo: Money/datas passam por serialização tipada; SQLAlchemy `JSON`
   type cuida do round-trip JSONB.
2. **Pooling** — SQLAlchemy `QueuePool` (não `psycopg_pool`); comportamento
   idêntico v2↔v3.
3. **Imports diretos de `psycopg2`** — grep confirma 0 em
   backend/pipeline/scripts (só via driver string do SQLAlchemy).

## Especialista pre-PR

- **`data-engineer`** (obrigatório, blocking) — **executado**. Derrubou a
  premissa asyncpg-only antes do PR (44 callsites Celery + Alembic-já-async);
  validou o swap psycopg3 com dois engines como caminho de risco mínimo.
  **Driver = decisão de DB layer.**
