---
id: ADR-253
type: adr
title: "Postgres driver consolidation (asyncpg-only) — Sprint A20"
status: Proposto
phase: A20.l8
date: "2026-05-22"
relates_to:
  - "[[ADR-111]]"
  - "[[ADR-248]]"
  - "[[ADR-254]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 253"
  - "asyncpg only"
  - "Postgres driver consolidation"
tags:
  - type/adr
  - status/proposto
  - area/infra
  - area/db
  - area/backend
  - phase/a20
---

## Contexto

Review independente `sre-devops` (2026-05-22) identificou **P1.2**: backend
carrega **dois drivers Postgres** simultaneamente:

- `psycopg2-binary` (sync engine, `backend/app/core/database.py:21`) —
  usado por Alembic + healthcheck sync.
- `asyncpg` (async engine, `database.py:52`) — usado pela aplicação FastAPI
  + SQLAlchemy 2.x async.

`backend/requirements.txt` carrega ambos; Dockerfile instala `libpq-dev`
(toolchain) + `libpq5` (runtime) para psycopg2-binary. Coexistência **não é
arquitetural** — é dívida acumulada de quando o codebase migrou
gradualmente para async.

Custo concreto:

- **+12MB wheel** + ~5MB libpq5 apt dep — bloqueia enxugar
  imagem `runtime` de [[A20.l1]] (target <450MB).
- **Mismatch de behavior** em edge cases (timezone, timestamp, NULL handling)
  entre os 2 drivers.
- **Surface de bug duplicada** — bug em qualquer dos 2 vira incidente.

Gap 1 do `senior-cto` review: "L8 (driver consolidation) como `opcional` é
red flag — dívida ativa não é opcional".

## Decisão

**Consolidar em `asyncpg`-only** com sync wrappers onde necessário (Alembic,
healthcheck):

- `backend/requirements.in` (após [[ADR-254]]) **remove** `psycopg2-binary`.
- `backend/app/core/database.py`: 1 engine async + helpers de sync via
  `asyncio.run_until_complete` para callsites que exigem sync.
- Alembic `env.py` adaptado: usa `asyncio.run(do_run_migrations())` para
  rodar migrations contra engine async.
- Dockerfile runtime stage ([[A20.l1]]) **remove** `libpq5` apt dep —
  asyncpg é puro-Python wheel.

**Fallback documentado:** se asyncpg-only inviável para Alembic em alguma
migration específica (driver-specific feature), usa `psycopg[binary]` v3
(não `psycopg2-binary` — psycopg v3 é mais leve, libpq3-ready, mantida
ativa). Documenta justificativa explícita em ADR atualização se exercido.

## Alternativas consideradas

### Opção A — Manter coexistência (`psycopg2-binary` + `asyncpg`)

**Rejeitada.** Não resolve dívida; bloqueia [[A20.l1]] de enxugar runtime
stage.

### Opção B — `psycopg[binary]` v3 only (sync) + remove asyncpg

**Rejeitada.** Inverte direção da migração histórica; quebra performance
async em endpoints da API. SQLAlchemy 2.x async perde melhor driver
(asyncpg é mais rápido que psycopg v3 async).

### Opção C — `asyncpg`-only com wrappers (**adotada**)

Resolve dívida + enxuga imagem + preserva performance async. Custo: 1
wrapper de sync em Alembic `env.py` e em healthcheck (já há precedente em
outros projetos Python — pattern conhecido).

### Opção D — Migrar para `psycopg[pool]` v3 unified (sync+async)

**Rejeitada para V1.** psycopg v3 suporta sync e async no mesmo pacote, mas
maturidade do modo async ainda < asyncpg (Q1 2026). Revisitar em A22+ se
asyncpg deprecation virar problema.

## Consequências

### Positivas

- **P1.2 resolvido** — driver único, surface de bug única.
- **Imagem `runtime` enxuga ~15MB** — sem libpq5 apt + sem psycopg2-binary
  wheel.
- **Mais simples para novo dev** — 1 driver, 1 engine, 1 mental model.
- **Stateless rigoroso preservado** ([[ADR-111]]) — engine async lazy
  singleton continua válido.

### Negativas

- **Wrappers de sync em Alembic + healthcheck** — overhead leve
  (`asyncio.run` start/stop ~50ms). Tolerável em path de boot e probe.
- **PR mais arriscado** — toca camada de DB. Mitigação: integration tests
  cobrindo `multi_worker_concurrency` rodando antes e depois.

### Neutras

- **`psycopg[binary]` v3 disponível como fallback** — se algum edge case
  obrigar; rota documentada.

## Validação

Critérios em [[A20.l8]] §"Critério de aceite" (5 critérios):

1. `backend/requirements.lock` **sem** `psycopg2-binary`/`psycopg2`.
2. Stage `runtime` sem `libpq5` apt dep.
3. Suíte completa verde.
4. Integration tests (multi_worker_concurrency) `p95 < baseline + 10%`.
5. `alembic upgrade head` em ambiente fresh verde.

## Migração

Fases em [[A20.l8]] §"Escopo IN":
1. [[ADR-254]] mergeada (lockfile com hashes).
2. Refactor `database.py` + Alembic `env.py`.
3. Smoke + integration tests verdes.
4. Dockerfile [[A20.l1]] atualiza removendo libpq5.

## Riscos

- **Quebra Alembic em migration legada** — PR de prova rodando `alembic
  downgrade -1 && alembic upgrade head` em todas migrations ativas.
- **Latência regressão** — integration tests medem p95.
- **Third-party libs assumindo psycopg2** — grep + substituir/wrap.

## Métricas

- Image size `runtime` (target -15MB vs baseline pós-[[A20.l1]]).
- p95 latency em integration tests (target +0% vs baseline; <10% acceptable).
- Linhas em `database.py` (target estável ou menor — não inflar com
  wrappers).

## Referências externas

- [asyncpg docs](https://magicstack.github.io/asyncpg/)
- [SQLAlchemy 2.x async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic async migrations](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic)
