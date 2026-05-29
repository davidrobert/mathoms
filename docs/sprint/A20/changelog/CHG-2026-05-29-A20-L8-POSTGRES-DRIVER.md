---
id: CHG-2026-05-29-A20-L8-POSTGRES-DRIVER
type: changelog-entry
date: "2026-05-29"
sprint: A20
lane: "[[A20.l8]]"
adrs: ["[[ADR-253]]"]
summary: |
  A20.L8 — swap do driver sync legado psycopg2-binary → psycopg[binary] v3
  (P1.2). Premissa original asyncpg-only foi derrubada por review blocking do
  data-engineer (sync engine drivea 44 callsites Celery; Alembic já é asyncpg);
  decisão invertida para swap de driver, mantendo dois engines. Remove
  libpq5/libpq-dev do Dockerfile (libpq embarcado no wheel binary).
  sync_database_url passa a emitir postgresql+psycopg:// explícito.
tags:
  - type/changelog-entry
  - sprint/a20
  - area/infra
  - area/db
  - area/devops
---

# A20.L8 — Postgres driver: psycopg2 → psycopg v3 swap

- **Driver legado eliminado** ([[ADR-253]] · resolve **P1.2**) —
  `psycopg2-binary` (modo manutenção) → `psycopg[binary]` v3 (linha ativa,
  mesmo autor). Apenas o extra `[binary]` (libpq embarcado no wheel; `[c]` ou
  puro reintroduziriam a apt dep).

- **Pivot de escopo via `data-engineer` (blocking, pré-PR).** A premissa
  original da lane ("asyncpg-only com sync wrapper") era factualmente errada:
  o sync engine drivea **44 arquivos** do task layer Celery (prefork síncrono),
  não só Alembic/healthcheck — e Alembic **já roda asyncpg**. asyncpg-only
  exigiria reescrever 44 callsites para async (event-loop por-task em prefork =
  bug conhecido). Decisão invertida para swap de driver, **dois engines
  mantidos**.

- **URL com driver explícito** — `config.py.sync_database_url` emite
  `postgresql+psycopg://`. O transform antigo deixava `postgresql://`, que o
  SQLAlchemy resolve para o **default psycopg2** (por omissão); sem o driver
  explícito o swap não pegaria. 2 testes unitários novos em
  `test_config_prod_gates.py` (postgres→psycopg3; sqlite→pysqlite default).

- **Dockerfile enxuga** — builder remove `libpq-dev`, runtime remove `libpq5`.
  psycopg v3 binary é wheel pré-compilado com libpq embarcado; asyncpg não
  linka libpq de sistema. Nenhum driver precisa da apt dep.

- **Lock regenerado** (container linux/amd64) — `psycopg==3.3.4` +
  `psycopg-binary`; `psycopg2` count = 0; `asyncpg==0.31.0` retido.

- **Verificação empírica** — imagem `mathoms-backend:l8test` builda exit 0 sem
  `libpq-dev`; `libpq5` ausente do runtime (`dpkg -l libpq5` exit 1);
  `import psycopg` (3.3.4) + `import asyncpg` (0.31.0) OK; suíte backend 2535
  passed / 4 skipped.

- **Débito remanescente (fora de A20)** — consolidação async do task layer
  Celery em 1 driver fica para lane A22+ com ADR própria. Estado atual: um
  driver async moderno (asyncpg) + um sync moderno (psycopg3), sem legado.
