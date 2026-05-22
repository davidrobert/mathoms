---
id: A20.l3
type: lane
title: "Docker dev↔prod parity — L3 pipeline-service non-root + healthcheck por service"
sprint: A20
status: open
priority: P0
branch_slug: a20-l3-pipeline-service-hardening
depends_on: []
parallel_with:
  - "[[A20.l2]]"
  - "[[A20.l6]]"
  - "[[A20.l10]]"
adrs_canonical:
  - "[[ADR-252]]"
tags:
  - type/lane
  - sprint/a20
  - status/ready
  - priority/p0
  - area/infra
  - area/docker
  - area/security
---

# A20.L3 — pipeline-service non-root + healthcheck por service

> **Onda A** em [[MOC-sprint-a20]]. Lane curtíssima (XS) que resolve **P0.4
> (pipeline-service rodando como root)** e **P1.1 (healthcheck no Dockerfile
> multi-modo quebrado)**.

## Resumo

[`pipeline-service/Dockerfile`](../../../../pipeline-service/Dockerfile) hoje não
tem `USER` — processo `uvicorn` roda como root. Combinado com `bind 0.0.0.0:8001`
e mount de código, é vetor de escape em compose multi-tenant. Adiciona user
`mathoms` UID 1000 (paridade com backend).

Adicionalmente, move healthcheck do [`Dockerfile`](../../../../Dockerfile)
backend (linha 56, hardcoded `curl /health` que falha em worker/beat) para
`docker-compose.prod.yml` por service. Cada container tem comando apropriado:

- `api` → `curl --fail http://localhost:8000/health`
- `worker` → `celery -A backend.celery_app inspect ping`
- `beat` → `test -f /tmp/celerybeat.pid` (PID file scheduler)
- `pipeline-service` → `curl --fail http://localhost:8001/health`

## Escopo IN

- `pipeline-service/Dockerfile`: adicionar `RUN useradd ... mathoms` + `USER
  mathoms` antes de `CMD`.
- Remover `HEALTHCHECK` do `Dockerfile` backend (linha 56) — move pro compose.
- `docker-compose.prod.yml`: adicionar bloco `healthcheck:` por service com
  comando apropriado, `interval: 30s`, `timeout: 5s`, `start_period: 30s`,
  `retries: 3`.
- Mesma estrutura em `docker-compose.dev.yml` (a ser criado em [[A20.l6]]).

## Escopo OUT

- Refactor maior do `pipeline-service` (entrypoint multi-modo, volume
  ownership) — débito separado.
- Mover backend healthcheck para outro local que não compose (k8s probes,
  consul, etc.) — non-goal.

## Pré-requisitos

- [[ADR-252]] mergeada como `Proposto` (cobre compose dev unificado + healthcheck
  policy — ver [[A20.l6]]).

## Critério de aceite

1. `docker inspect pipeline-service --format '{{.Config.User}}'` retorna
   `mathoms` (não vazio, não `root`).
2. `docker run --rm pipeline-service:test whoami` imprime `mathoms`.
3. `docker-compose up -d && sleep 60` seguido de `docker-compose ps --format
   json | jq -r '.[].Health'` retorna `healthy` para **todos** os services
   (5+: postgres, redis-broker, redis-cache, api, worker, beat, frontend,
   pipeline-service quando ativo).
4. `docker exec <worker-container> celery -A backend.celery_app inspect ping`
   retorna `pong` em ≤2s.
5. Backend Dockerfile não tem mais `HEALTHCHECK` instruction (`grep
   HEALTHCHECK Dockerfile` retorna vazio).

## Definition of Done

- [ ] PR mergeado em `main` com CI verde.
- [ ] [[ADR-252]] referencia esta lane (sub-decisão de healthcheck por service).
- [ ] Smoke local em macOS + Linux: compose sobe, todos healthy em <90s.
- [ ] Runbook `docs/reference/runbooks/docker_healthchecks.md` documenta como
      debugar healthcheck flaky.
- [ ] [CHANGELOG](../../../CHANGELOG.md) entry registrada.

## Riscos top 3

1. **Celery `inspect ping` cresce custoso em fleet grande** — em fleet de 1
   worker (atual) é barato; futuro autoscale precisa cachear. Mitigação:
   `start_period: 30s` evita probe agressivo; revisitar quando worker = N+1.
2. **PID file `/tmp/celerybeat.pid` pode ficar stale após crash** — mitigação:
   `entrypoint.sh` deleta PID antigo no início; healthcheck também valida
   freshness (`find /tmp/celerybeat.pid -mmin -2`).
3. **pipeline-service hoje sem volume `:ro` quebra em runtime?** — testar
   `docker run --read-only pipeline-service:test` no smoke; se quebrar, é
   bug separado (não bloquear A20.L3).

## Especialista pre-PR

- **`sre-devops`** (obrigatório) — review do healthcheck Celery worker
  (comando correto sem polling caro) + UID 1000 em pipeline-service.
