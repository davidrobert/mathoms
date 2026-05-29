---
id: TRACK-a20-l1-backend-multistage
type: track
title: "Track A20.L1 — Backend multi-stage + Playwright dual target"
lane: "[[A20.l1]]"
sprint: A20
status: consumed
created_at: "2026-05-29"
agent_role: sre-devops
tags:
  - type/track
  - sprint/a20
  - status/consumed
  - priority/p0
  - area/infra
  - area/docker
  - area/devops
---

# Track A20.L1 — Backend multi-stage + Playwright dual target

> **Lane canônica:** [[A20.l1]] — contém o **Dockerfile completo de 3 stages** (builder → runtime → playwright), compose prod por service, workflow GHCR, estratégia de cache, critério de aceite (10 itens) e DoD. Use a lane como source-of-truth literal.
> · **ADR canônica:** [[ADR-248]] (`Proposto`, Opção C — dual target, 1 Dockerfile).
> · **Branch prefix:** `agent/a20-l1-backend-multistage/*`
> · **Onda B** — **pré-requisito rígido: [[A20.l10]] mergeada** (lockfile existe). Gate de merge conjunto com [[A20.l2]] (SHA pin no `ARG PYTHON_BASE_SHA`).

## Briefing

Refatora o `Dockerfile` único atual (single-stage `python:3.12-slim`, ~1.1GB) em 3 stages com 2 targets publicáveis: `runtime` (<450MB — worker/beat) e `playwright` (<950MB — api, herda 100% de runtime + Chromium). Resolve P0.1 (api precisa Playwright p/ PDF [[ADR-076]], worker/beat não — hoje todos carregam Chromium morto) + P0.3 (multi-stage).

Invariante auditável: container rodando target `runtime` **nunca** tem processo `chromium`/`node` (`ps -ef` vazio no smoke).

## Pré-flight (documentar no PR)

```bash
git fetch origin && git worktree list      # nenhum agente em a20-l1
ls docs/adr/248-*.md                        # ADR-248 em main
git log origin/main --oneline | grep -i a20-l10   # L10 mergeada (lockfile existe)
ls requirements.lock backend/requirements.lock    # lockfiles presentes
docker buildx version
```

## Execução (lane traz o Dockerfile literal — copie e adapte)

1. Substituir `Dockerfile` pelo multi-stage da [[A20.l1]] §"Dockerfile multi-stage". `ARG PYTHON_BASE_SHA` placeholder até L2 pinar.
2. `entrypoint.sh` aceita `api`/`worker`/`beat` como CMD (verificar `backend/scripts/entrypoint.sh` atual).
3. `docker-compose.prod.yml`: `api → playwright-<sha>`, `worker`/`beat → runtime-<sha>`.
4. `docker-compose.dev.yml` ([[A20.l6]]) usa target `playwright` default (dev mantém PDF).
5. Runbook `docs/reference/runbooks/docker_images.md` ("quando trocar target", "auditar enxutez do worker").
6. Validar os 10 critérios de aceite — especialmente tamanho (`docker image inspect`), smoke PDF render, audit worker sem Chromium, heredity (`docker history`).

## Especialistas pre-PR

- **`sre-devops`** (obrigatório) — Dockerfile multi-stage, healthcheck, non-root, layer ordering, ausência de secrets em ENV.
- **`build-vs-buy`** (consultivo) — confirmar Playwright como engine PDF segue [[ADR-076]] (sem janela de revisão de provedor agora).

## Definition of Done

Ver [[A20.l1]] §"Definition of Done". Resumo: PR em `main` CI verde; [[ADR-248]] `Decidido`; compose prod/dev atualizados; runbook `docker_images.md`; smoke staging (3 PDFs render + 1 task Celery sem stack-trace).

## Ligações

- **Lane:** [[A20.l1]] · **ADR:** [[ADR-248]] · **Sprint MOC:** [[MOC-sprint-a20]]
- **Upstream:** [[A20.l10]] (lockfile), [[A20.l2]] (SHA pin) · **Downstream:** [[A20.l4]] (GHCR builda os 2 targets), [[A20.l9]] (smoke E2E).
