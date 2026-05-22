---
id: A20.l8
type: lane
title: "Docker dev↔prod parity — L8 Postgres driver consolidation (asyncpg-only)"
sprint: A20
status: open
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
  - status/ready
  - priority/p1
  - area/infra
  - area/db
  - area/devops
---

# A20.L8 — Postgres driver consolidation (asyncpg-only)

> **Onda B** em [[MOC-sprint-a20]] — **obrigatória** (gap 1 do `senior-cto`).
> Resolve **P1.2** (coexistência `psycopg2-binary` + `asyncpg` é dívida ativa).

## Resumo

Coexistência de `psycopg2-binary` (sync engine,
[`database.py:21`](../../../../backend/app/core/database.py)) + `asyncpg` (async
engine, `database.py:52`) é **dívida ativa**, não débito tolerado: duplica
drivers no container (`libpq5` apt dep + psycopg2-binary wheel ~12MB),
duplica surface de bug (mismatch de behavior em edge cases de
timezone/timestamp), e bloqueia enxugar imagem `runtime` ([[A20.l1]]).

Consolida em **asyncpg-only** com sync wrapper via `asyncio.run_until_complete`
onde Alembic e healthchecks exigem sync. Decisão final em [[ADR-253]];
recomendação inicial PM: asyncpg-only, com `psycopg[binary]` v3 (não
`psycopg2-binary`) como fallback estrito se asyncpg-only inviável para
Alembic.

## Escopo IN

- [[ADR-253]] decide driver final (`asyncpg-only` recomendado; `psycopg[binary]`
  v3 fallback se necessário).
- `backend/requirements.in` (após [[A20.l10]]) remove `psycopg2-binary`.
- `backend/app/core/database.py` consolida: 1 engine assíncrona +
  helpers/wrappers de sync onde necessário (Alembic, healthcheck).
- Alembic env adaptado para usar driver consolidado (provavelmente
  `asyncio.run` wrapper em `env.py`).
- Dockerfile [[A20.l1]] runtime stage **remove** `libpq5` apt dep (asyncpg
  é puro-Python wheel — não precisa libpq sistema).
- Suíte completa verde (`pytest backend/tests -q` + `pytest tests -q` +
  integration tests).

## Escopo OUT

- Migrar para `sqlmodel` ou outro ORM — non-goal.
- Substituir Alembic — non-goal.
- Cache de connection pool diferente — não relacionado.

## Pré-requisitos

- [[ADR-253]] mergeada como `Proposto`.
- [[A20.l10]] mergeada (lockfile existe).
- [[A20.l1]] em paralelo — coordenação para remover `libpq5` da runtime stage.

## Critério de aceite

1. `backend/requirements.lock` (pós-[[A20.l10]]) **não contém**
   `psycopg2-binary` nem `psycopg2`.
2. Stage `runtime` do Dockerfile ([[A20.l1]]) **não instala** `libpq5` via apt
   (validado por `docker run --rm mathoms-backend:runtime-<sha> dpkg -l libpq5`
   retornar exit code 1 — pacote não encontrado).
3. Suíte completa verde: `pytest backend/tests -q` + `pytest tests -q` sem
   skip ou xfail novos.
4. Integration tests que tocam Postgres real
   (`test_multi_worker_concurrency.py` e correlatos) passam com novo driver
   sem regressão de latência (`p95 < baseline + 10%`).
5. `alembic upgrade head` em ambiente fresh funciona sem erro.

## Definition of Done

- [ ] PR mergeado em `main` com CI verde.
- [ ] [[ADR-253]] promovida `Proposto → Decidido (A20.L8)`.
- [ ] `psycopg2-binary` removido de todos os `requirements*.txt`/`.in`/`.lock`.
- [ ] Image size `runtime` reportada pós-merge (esperado ~-15MB vs com
      `libpq5` + psycopg2 wheel).
- [ ] Smoke local + integration tests verdes.
- [ ] [CHANGELOG](../../../CHANGELOG.md) entry registrada.

## Riscos top 3

1. **Quebra Alembic em alguma migration legada** — Alembic historicamente
   prefere sync. Mitigação: PR de prova rodando `alembic downgrade -1 &&
   alembic upgrade head` em todas migrations ativas; se quebrar, fallback
   `psycopg[binary]` v3 documentado em [[ADR-253]].
2. **Latência regressão em queries complexas** — asyncpg em queries com
   muitos joins pode comportar diferente de psycopg2. Mitigação: integration
   tests medem p95 latency; flag se >10% regressão.
3. **Bibliotecas third-party assumem psycopg2** — algumas libs Python têm
   driver hardcoded. Mitigação: grep no codebase por imports diretos de
   `psycopg2`; substituir ou wrap.

## Especialista pre-PR

- **`data-engineer`** (obrigatório, blocking) — review da consolidação de
  driver. Foco em: Alembic compat, behavior diff timezone/timestamp,
  connection pooling, transaction isolation. **Driver = decisão de DB
  layer, não de DevOps.**
