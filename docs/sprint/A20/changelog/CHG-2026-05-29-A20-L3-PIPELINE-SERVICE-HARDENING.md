---
id: CHG-2026-05-29-A20-L3-PIPELINE-SERVICE-HARDENING
type: changelog-entry
date: "2026-05-29"
sprint: A20
lane: "[[A20.l3]]"
adrs: ["[[ADR-252]]"]
summary: |
  A20.L3 — pipeline-service non-root (P0.4) + healthcheck por service (D4).
  pipeline-service ganha user mathoms UID 1000 + HEALTHCHECK urllib; backend
  Dockerfile perde o HEALTHCHECK multi-modo (movido pro compose); worker ganha
  `celery inspect ping`, beat fica sem healthcheck (PID 1 + restart policy).
  Fecha o último gate de ADR-252 → Decidido.
tags:
  - type/changelog-entry
  - sprint/a20
  - area/infra
  - area/docker
  - area/security
---

# A20.L3 — pipeline-service non-root + healthcheck por service

- **pipeline-service não-root** ([[ADR-252]] D4 · resolve **P0.4**):
  `useradd -u 1000 mathoms` (mesmo UID do backend) + `chown -R /repo` +
  `USER mathoms` antes do CMD. Antes rodava como **root** com `bind
  0.0.0.0:8001` — vetor de escape em compose multi-tenant.
- **HEALTHCHECK do pipeline-service no Dockerfile** (single-modo): via
  `urllib` (base `python:3.12-slim` não traz curl) com `timeout=5` no
  `urlopen`.
- **Backend Dockerfile perde o `HEALTHCHECK`** ([[ADR-252]] D4 · resolve
  **P1.1**): a imagem é multi-modo (api/worker/beat) e `curl /health` só vale
  para o api. Cada service declara o seu no compose.
- **Healthcheck por service** em `docker-compose.prod.yml` +
  `docker-compose.dev.yml`:
  - `worker` → `celery -A backend.app.worker inspect ping` (broadcast;
    `timeout: 15s`, `start_period: 45s`, `retries: 3`). Substitui o
    `disable: true` anterior.
  - `beat` → **sem healthcheck** (decisão sre-devops): beat é PID 1 → crash
    reinicia via `restart: unless-stopped`. `inspect ping` é só para workers;
    pidfile fica stale e mascara morte.
  - `api` → inalterado (`curl /health`, `start_period: 60s` por alembic).
- **Correção vs draft**: o módulo Celery é `backend.app.worker` (lane dizia
  `backend.celery_app` — path inexistente). Build do pipeline-service estava
  quebrado (`pip install` rodava antes do `COPY` do source — setuptools falha
  com "package directory 'app' does not exist"); reordenado COPY antes do
  install para tornar o fix non-root verificável.
- **Runbook** `docs/reference/runbooks/docker_healthchecks.md`: onde cada
  healthcheck vive e por quê, debug de probe flaky, checklist de service novo.
- **[[ADR-252]] → `Decidido`**: L3 (D4) era o último gate, com L6 (D1/D2) e
  L7 (D3/D5) já mergeados.
