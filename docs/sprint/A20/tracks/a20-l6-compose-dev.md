---
id: TRACK-a20-l6-compose-dev
type: track
title: "Track A20.L6 — docker-compose.dev.yml unificado + cleanup composes legados"
lane: "[[A20.l6]]"
sprint: A20
status: consumed
created_at: "2026-05-29"
agent_role: sre-devops
tags:
  - type/track
  - sprint/a20
  - status/consumed
  - priority/p1
  - area/infra
  - area/devops
  - area/dx
---

# Track A20.L6 — `docker-compose.dev.yml` unificado

> **Lane canônica:** [[A20.l6]] (tabela de decisão de cleanup, escopo IN/OUT, critério de aceite, DoD).
> · **ADR canônica:** [[ADR-252]] (`Proposto`, compartilhada com L3/L7).
> · **Branch prefix:** `agent/a20-l6-compose-dev-unified/*`
> · **Onda A** — disjunto, **paraleliza com [[A20.l3]]** (L6 toca `docker-compose*.yml`, L3 toca `pipeline-service/*`).

## Briefing

Cria `docker-compose.dev.yml` orquestrando stack completa local (7 services: postgres, redis-broker, redis-cache, api, worker, beat, frontend) com hot-reload (`uvicorn --reload`, bind mounts `delegated`/`cached` p/ macOS), seed automático idempotente (`entrypoint.dev.sh`: alembic + `dev/seed_minimal_workspace.py` se DB vazio). Resolve P1.6. North star: `up -d` em clone fresh → stack healthy <120s.

**Cleanup (gap 3 senior-cto):** deleta `docker-compose.yml` (Redis-only redundante); reescreve `docker-compose.dev.yml` (antes só frontend-ops); mantém prod/smoke/test/pipeline-service. Total pós-A20: 4 composes (era 5).

## Pré-flight (documentar no PR)

```bash
git fetch origin && git worktree list      # nenhum agente em a20-l6/a20-l3
ls docs/adr/252-*.md
ls docker-compose*.yml                       # inventário atual (5 files)
docker compose version                       # v2.20+ (suporta include:)
```

## Execução (resumo — detalhe em [[A20.l6]])

1. Novo `docker-compose.dev.yml` (7 services, healthchecks coordenados com [[A20.l3]], mounts documentados inline).
2. `entrypoint.dev.sh` idempotente (seed `ON CONFLICT DO NOTHING` ou check upfront).
3. `docker-compose.dev.override.yml.example` (vars locais; o real não é versionado).
4. `uvicorn --reload --reload-dir backend/app` (não watch `/app` inteiro).
5. **Deletar** `docker-compose.yml`.
6. Runbook `docs/reference/runbooks/dev_environment.md` substitui seção "subir Postgres local" do [SETUP](../../../reference/SETUP.md).
7. Validar TTFR <120s em macOS Apple Silicon (`--platform linux/amd64`) + Linux.

## Especialista pre-PR

- **`sre-devops`** (obrigatório) — compose, mount strategy, seed idempotência, healthchecks (coordenar com [[A20.l3]]).

## Definition of Done

Ver [[A20.l6]] §"Definition of Done". Resumo: PR em `main` CI verde; `docker-compose.yml` deletado; runbook `dev_environment.md`; TTFR <120s medido 3× em macOS+Linux; CHANGELOG.

## Ligações

- **Lane:** [[A20.l6]] · **ADR:** [[ADR-252]] · **Sprint MOC:** [[MOC-sprint-a20]]
- **Paraleliza:** [[A20.l3]] (healthchecks) · **Downstream:** [[A20.l1]] (target playwright default), [[A20.l7]] (Makefile `docker-up` aponta p/ este compose), [[A20.l9]] (smoke usa este compose).
