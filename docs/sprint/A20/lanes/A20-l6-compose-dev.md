---
id: A20.l6
type: lane
title: "Docker dev↔prod parity — L6 docker-compose.dev.yml unificado + cleanup composes legados"
sprint: A20
status: open
priority: P1
branch_slug: a20-l6-compose-dev-unified
depends_on: []
parallel_with:
  - "[[A20.l2]]"
  - "[[A20.l3]]"
  - "[[A20.l10]]"
adrs_canonical:
  - "[[ADR-252]]"
tags:
  - type/lane
  - sprint/a20
  - status/ready
  - priority/p1
  - area/infra
  - area/devops
  - area/dx
---

# A20.L6 — `docker-compose.dev.yml` unificado + cleanup composes legados

> **Onda A** em [[MOC-sprint-a20]] (paralela a L2/L3/L10). Núcleo do gap dev↔prod.
> Resolve **P1.6** (dev local não usa Docker). Decide explicitamente quais dos
> 5 compose files existentes morrem ou consolidam (gap 3 do `senior-cto`
> review).

## Resumo

Cria `docker-compose.dev.yml` orquestrando stack completa para dev local com
**hot-reload** (`./backend:/app/backend:ro` + `uvicorn --reload`), seed
automático de DB (Alembic + fixtures sintéticas em primeiro up), override
`.example` para vars locais. Substitui `docker-compose.yml` (Redis-only) +
`docker-compose.dev.yml` (frontend-ops apenas) + `docker-compose.smoke.yml`
para o caso dev — `smoke.yml` continua existindo só para CI smoke.

## Decisão de cleanup de composes (gap 3 senior-cto)

Estado atual: 5 compose files (`docker-compose.yml`, `docker-compose.dev.yml`,
`docker-compose.prod.yml`, `docker-compose.smoke.yml`, `docker-compose.test.yml`)
+ `pipeline-service/docker-compose.yml` separado.

Decisão (escopo [[ADR-252]]):

| Arquivo | Decisão | Motivo |
|---|---|---|
| `docker-compose.yml` (Redis dev) | **DELETAR** | Redundante com novo `dev.yml` |
| `docker-compose.dev.yml` (frontend-ops antigo) | **REESCRITO** | Vira o novo dev unificado |
| `docker-compose.prod.yml` | **MANTER** | Source-of-truth do prod |
| `docker-compose.smoke.yml` | **MANTER** | CI smoke (efêmero Redis) |
| `docker-compose.test.yml` | **MANTER** | E2E local (Postgres 5433 + Redis 6380) |
| `pipeline-service/docker-compose.yml` | **MANTER** | Service-específico |

**Total pós-A20: 4 compose files** (era 5). Frontend-ops cobertura migra para
override file do `dev.yml`.

## Escopo IN

- Novo `docker-compose.dev.yml` com 7 services: `postgres`, `redis-broker`,
  `redis-cache`, `api`, `worker`, `beat`, `frontend`.
- Volumes para hot-reload:
  - `./backend:/app/backend:ro,delegated` (macOS optimized)
  - `./frontend:/app/frontend:cached`
  - `./config:/app/config:ro`
- `uvicorn --reload` em api command.
- Seed automático: `entrypoint.dev.sh` que roda `alembic upgrade head` +
  `python dev/seed_minimal_workspace.py` se DB vazio.
- Override file `docker-compose.dev.override.yml.example` documentando vars
  locais (não versionado real, só example).
- `docker-compose.yml` deletado.
- Documentação inline (comentários YAML) explicando cada decisão de mount.

## Escopo OUT

- Hot-reload do frontend (Next.js dev server já tem; mantém via `npm run dev`
  dentro do container).
- Substituir `smoke.yml` ou `test.yml` — escopo isolado.
- `docker-compose.ci.yml` dedicado para CI (gap 4 senior-cto adiado).

## Pré-requisitos

- [[ADR-252]] mergeada como `Proposto`.
- [[A20.l10]] em paralelo — lockfile existe para builder stage.

## Critério de aceite

1. `docker-compose -f docker-compose.dev.yml up -d` em clone fresh sobe stack
   completa em **<120s wall-clock** (medido com `time`).
2. Alterar arquivo em `backend/app/api/` triggera reload do uvicorn em **<3s**
   (detectável via logs).
3. `docker-compose -f docker-compose.dev.yml exec api curl --fail
   http://localhost:8000/health` retorna 200.
4. DB seedado tem ≥1 workspace + family_members (verificado via `docker-compose
   exec postgres psql -U mathoms -d mathoms -c 'select count(*) from
   workspaces'` → ≥1).
5. Testado em macOS Apple Silicon (via Rosetta `--platform linux/amd64`) e
   Linux x86_64.
6. `docker-compose.yml` deletado do repo.

## Definition of Done

- [ ] PR mergeado em `main` com CI verde.
- [ ] [[ADR-252]] referencia esta lane (sub-decisão de compose dev + cleanup).
- [ ] `docker-compose.yml` (Redis-only) deletado.
- [ ] Runbook `docs/reference/runbooks/dev_environment.md` substitui seção
      antiga de "subir Postgres local" em [SETUP](../../../reference/SETUP.md).
- [ ] Smoke local em macOS + Linux: TTFR medido <120s em 3 execuções.
- [ ] [CHANGELOG](../../../CHANGELOG.md) entry registrada.

## Riscos top 3

1. **Performance de bind mount em macOS** — bind mount NFS sem
   `delegated`/`cached` é lento. Mitigação: `delegated` mount strategy
   documentado em [[ADR-252]]; fallback `cached`; alternativa final: rebuild
   rápido (`make dev-rebuild` em <30s).
2. **Seed automático falha em re-run** — `entrypoint.dev.sh` precisa idempotent;
   se workspaces já existe, pula seed sem erro. Mitigação: `INSERT ... ON
   CONFLICT DO NOTHING` ou check upfront.
3. **`uvicorn --reload` consome 100% CPU em watching de muito arquivo** —
   mitigação: `--reload-dir backend/app` (não watch todo `/app`); `--reload-include
   *.py` exclude templates.

## Especialista pre-PR

- **`sre-devops`** (obrigatório) — review do compose + mount strategy + seed
  idempotência + healthchecks (coordenado com [[A20.l3]]).

## Detalhe operacional

Track prompt em [`../tracks/a20-l6-compose-dev.md`](../tracks/a20-l6-compose-dev.md) (criado 2026-05-29; pós-F3/ADR-182 tracks vivem em `docs/sprint/<X>/tracks/`).
