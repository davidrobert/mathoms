---
id: ADR-253
type: adr
title: "Postgres driver — drop psycopg2 → psycopg v3 (sync) — Sprint A20"
status: Decidido
phase: A20.l8
date: "2026-05-22"
amended_at: ["2026-05-29"]
relates_to:
  - "[[ADR-111]]"
  - "[[ADR-248]]"
  - "[[ADR-254]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 253"
  - "psycopg3 swap"
  - "Postgres driver consolidation"
tags:
  - type/adr
  - status/decidido
  - area/infra
  - area/db
  - area/backend
  - phase/a20
---

## Contexto

Review independente `sre-devops` (2026-05-22) identificou **P1.2**: backend
carrega **dois drivers Postgres** simultaneamente:

- `asyncpg` (async engine, `backend/app/core/database.py`) — endpoints FastAPI
  + SQLAlchemy 2.x async **e Alembic** (`alembic/env.py` já roda
  `async_engine_from_config` + `asyncio.run`).
- `psycopg2-binary` (sync engine, `database.py`) — `SyncSessionLocal`.

`Dockerfile` instala `libpq-dev` (builder) + `libpq5` (runtime) para
psycopg2-binary. Coexistência **não é arquitetural** — é dívida acumulada da
migração gradual para async.

Custo concreto:

- **+12MB wheel** + ~5MB libpq5 apt dep — bloqueia enxugar imagem `runtime`
  de [[A20.l1]] (target <450MB).
- **`psycopg2` está em modo manutenção** — psycopg v3 é a linha ativa,
  mantida pelo mesmo autor; manter o legado é dívida que só cresce.

### Correção de premissa (co-design `data-engineer`, 2026-05-29)

A primeira versão desta ADR (`Proposto`) tinha **premissa factual errada em
dois pontos**, descoberta na review blocking do `data-engineer` antes do PR:

1. **O sync engine não é "Alembic + healthcheck".** `grep` confirma **44
   arquivos** consumindo `SyncSessionLocal`/`sync_engine`: a espinha dorsal é
   o **task layer Celery inteiro** (workers prefork, síncronos —
   `tasks/pipeline_task.py` com ~20 callsites, `categorization_apply.py`,
   `lgpd_export.py`, `fipe_refresh.py`, `periodic_tasks.py`), além de
   services sync, 1 endpoint (`api/categorization_rules.py`) e scripts.
2. **Alembic NEM USA o sync engine.** `env.py` já roda async (asyncpg). A
   recomendação original de "adaptar Alembic via `asyncio.run`" descrevia
   algo que **já existe**.

Essa correção **inverteu a decisão**: asyncpg-only exigiria reescrever 44
callsites síncronos do Celery para async (prefork + asyncio = event-loop
por-task, território de bug conhecido), o oposto de "reduzir surface de bug".

## Decisão

**Trocar o driver sync legado: `psycopg2-binary` → `psycopg[binary]` v3.
Manter a arquitetura de dois engines.**

- `engine` async (asyncpg) — endpoints FastAPI + Alembic. **Inalterado.**
- `sync_engine` (psycopg v3) — task layer Celery + scripts. **Inalterado em
  callsites**; muda só o driver por baixo.
- `backend/requirements.in`: `psycopg2-binary>=2.9` → `psycopg[binary]>=3.2`.
  **Apenas o extra `[binary]`** — traz libpq embarcado no wheel; `psycopg[c]`
  ou `psycopg` puro reintroduziriam a apt dep de sistema.
- `config.py.sync_database_url`: emite `postgresql+psycopg://` **explícito**.
  O transform antigo (`replace("+asyncpg","")`) deixava `postgresql://`, que o
  SQLAlchemy resolve para o **default psycopg2** — por omissão, não por
  escolha. Sem o driver explícito o swap não pega.
- `Dockerfile`: **remove `libpq5`** (runtime) **e `libpq-dev`** (builder) —
  psycopg v3 binary é wheel pré-compilado com libpq embarcado; asyncpg não
  linka libpq de sistema. Nenhum driver precisa da apt dep.

**Consolidação real em 1 driver** (migração async do task layer Celery) fica
para lane futura (A22+), com ADR e gate próprios. Não se força em A20.

## Alternativas consideradas

### Opção A — Manter coexistência (`psycopg2-binary` + `asyncpg`)

**Rejeitada.** Não resolve dívida; bloqueia [[A20.l1]] de enxugar runtime
stage; mantém driver legado em modo manutenção.

### Opção B — `asyncpg`-only com sync wrappers (recomendação original, derrubada)

**Rejeitada** (co-design `data-engineer`). Premissa de que o sync engine só
serve Alembic/healthcheck era falsa — ele drivea 44 arquivos do task layer
Celery. Wrappear cada callsite com `asyncio.run()` cria/destrói event loop
por chamada (vaza conexão, quebra pool sob carga); um loop persistente cross-
thread esbarra em `AsyncSession` não ser thread-safe. Bug silencioso que não
aparece em SQLite e explode em Postgres prod. Viola o espírito de [[ADR-111]].

### Opção C — `psycopg[binary]` v3 swap, dois engines (**adotada**)

Atinge o ganho concreto de P1.2 (imagem enxuga sem libpq) + elimina o driver
**legado** (psycopg2) preservando performance async (asyncpg) nos endpoints.
Risco baixíssimo: não toca os 44 callsites; muda string de conexão + 1 linha
de requirements. "Consolidação no sentido que importa": um driver async
moderno + um sync moderno, sem legado.

### Opção D — `psycopg[pool]` v3 unified (sync+async, 1 driver)

**Rejeitada para A20.** psycopg v3 suporta sync e async no mesmo pacote, mas
o modo async ainda é < asyncpg em maturidade/perf (Q1 2026), e unificar
exigiria migrar o task layer. Revisitar em A22+.

## Consequências

### Positivas

- **P1.2 resolvido** — imagem `runtime` perde libpq5 (apt) + psycopg2 wheel.
- **Driver legado eliminado** — psycopg v3 é a linha ativa.
- **Risco baixo** — paradigma async (FastAPI/asyncpg) intocado; sync path só
  troca a implementação C que fala libpq.
- **Stateless rigoroso preservado** ([[ADR-111]]) — dois engines lazy
  singleton idempotentes continuam válidos.

### Negativas

- **Não consolida em 1 driver** — título original prometia demais. Dois
  drivers permanecem (asyncpg async + psycopg3 sync), mas ambos modernos.
- **Gotcha de URL** — `sync_database_url` precisava do driver explícito;
  coberto por teste unitário (`test_config_prod_gates.py`).

### Neutras

- **Migração async do task layer** — débito real, mas fora de escopo A20.

## Validação

Critérios em [[A20.l8]] §"Critério de aceite" (ajustados ao caminho psycopg3):

1. `requirements.lock` **sem** `psycopg2-binary`/`psycopg2` — ✔ (regen verde).
2. Stage `runtime` sem `libpq5`/`libpq-dev` apt dep — ✔.
3. Suíte completa verde.
4. **Reduzido a smoke de paridade de driver** (não "p95 sob mudança de
   paradigma" — o paradigma async não muda). Round-trip de artifact JSONB +
   query `timestamptz` na suíte de integração Postgres-real confirmam
   paridade psycopg2→psycopg3.
5. `alembic upgrade head` fresh verde — Alembic é asyncpg, intocado.

### Notas de entrega — L8 (2026-05-29)

- **Swap aplicado:** `requirements.in` → `psycopg[binary]>=3.2`; lock
  regenerado em container linux/amd64 (`psycopg==3.3.4` + `psycopg-binary`;
  `psycopg2` count = 0; asyncpg retido).
- **URL explícita:** `sync_database_url` emite `postgresql+psycopg://`;
  SQLAlchemy resolve `e.dialect.driver == "psycopg"` (validado em container).
  2 testes unitários novos (postgres → psycopg3; sqlite → pysqlite default).
- **Imagem:** lock instala **sem `libpq-dev`** em `python:3.12-slim`
  (`all core imports OK`, `psycopg 3.3.4`) — confirma libpq embarcado no
  wheel. Dockerfile builder perde `libpq-dev`, runtime perde `libpq5`.
- **Sem psycopg2 hardcoded:** grep confirma 0 imports diretos de `psycopg2`
  em backend/pipeline/scripts (só via driver string do SQLAlchemy).
- **Runbook** `python_dependencies.md` atualizado (validação importa
  `psycopg`, não `psycopg2`; sem `libpq-dev` no apt).

## Migração

1. [[ADR-254]] mergeada (lockfile com hashes) — pré-req ✔.
2. `requirements.in` swap + `config.py` driver explícito.
3. Regen `requirements.lock` (container amd64) + validação de import.
4. Dockerfile remove `libpq-dev` + `libpq5`.
5. Suíte + integração verdes.

## Riscos

- **Behavior diff psycopg2→psycopg3** (timezone/timestamp/JSONB/NULL) —
  mitigado por round-trip JSONB + `timestamptz` na integração Postgres-real.
  Baixo: Money/datas passam por serialização tipada; SQLAlchemy `JSON` type
  cuida do round-trip JSONB.
- **Pooling** — SQLAlchemy `QueuePool` (não `psycopg_pool`); comportamento
  idêntico v2↔v3.

## Métricas

- Image size `runtime` — esperado -15MB vs com libpq5 + psycopg2 wheel
  (validar empírico pós-merge).
- Linhas em `database.py` — **inalteradas** (swap é em requirements + config).

## Referências externas

- [psycopg 3 docs](https://www.psycopg.org/psycopg3/docs/)
- [SQLAlchemy — psycopg (v3) dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)
- [asyncpg docs](https://magicstack.github.io/asyncpg/)
