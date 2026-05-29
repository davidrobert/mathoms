---
id: CHG-2026-05-29-A20-L6-COMPOSE-DEV
type: changelog-entry
date: "2026-05-29"
sprint: A20
lane: "[[A20.l6]]"
adrs: ["[[ADR-252]]"]
summary: |
  A20.L6 — docker-compose.dev.yml unificado (D1+D2). Stack dev completa em
  Docker (7 services + hot-reload + seed automático), cleanup de compose
  legado (docker-compose.yml deletado), runbook dev_environment.md. Bug
  latente de paridade dev↔prod corrigido em PR separado (adr223 SET DEFAULT
  0 em coluna BOOLEAN — Postgres DatatypeMismatchError).
tags:
  - type/changelog-entry
  - sprint/a20
  - area/infra
  - area/devops
  - area/dx
---

# A20.L6 — `docker-compose.dev.yml` unificado + cleanup

- **`docker-compose.dev.yml` reescrito** ([[ADR-252]] D1): 7 services
  (`postgres`, `redis-broker`, `redis-cache`, `api`, `worker`, `beat`,
  `frontend` + `frontend-ops` via `--profile ops`), hot-reload via bind
  mount `./backend:ro` + `uvicorn --reload --reload-dir backend/app`, seed
  automático (`dev/entrypoint.dev.sh` → `alembic upgrade head` +
  `dev/seed_minimal_workspace.py` idempotente).
- **Cleanup de composes** ([[ADR-252]] D2): `docker-compose.yml` (Redis-only)
  deletado; `docker-compose.dev.override.yml.example` versionado (override
  real gitignored).
- **Paridade prod**: Redis broker `noeviction` + cache `allkeys-lru`,
  named volumes para pgdata/redisdata/storage, sem `:delegated`/`:cached`
  (no-op VirtioFS).
- **Runbook** `docs/reference/runbooks/dev_environment.md` + pointer no topo
  de [SETUP](../../../reference/SETUP.md); `ARCHITECTURE.md` atualizado.
- **Bug de paridade corrigido (PR separado)**: migration `adr223` emitia
  `SET DEFAULT 0` em coluna BOOLEAN — Postgres rejeita
  (`DatatypeMismatchError`); só SQLite tolerava. Fix: literal de default por
  dialeto. Exposto justamente pelo boot Docker contra Postgres real.
- **Validação empírica (macOS)**: `up -d --build` → `/health` 200
  (`database/redis/redis_cache: ok`), `alembic_version` na head, seed = 1
  workspace, hot-reload confirmado. Validação Linux x86_64 fica para o job
  de CI smoke ([[A20.l9]]).
- **ADR-252 permanece `Proposto`** até L3 (D4) + L7 (D3/D5) entrarem.
