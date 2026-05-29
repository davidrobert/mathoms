---
id: A20.l2
type: lane
title: "Docker dev↔prod parity — L2 SHA pinning de bases + Dependabot Docker"
sprint: A20
status: shipped
priority: P0
branch_slug: a20-l2-sha-pinning-dependabot
depends_on: []
parallel_with:
  - "[[A20.l3]]"
  - "[[A20.l6]]"
  - "[[A20.l10]]"
adrs_canonical:
  - "[[ADR-249]]"
tags:
  - type/lane
  - sprint/a20
  - status/shipped
  - priority/p0
  - area/infra
  - area/docker
  - area/security
---

# A20.L2 — SHA pinning de bases + Dependabot Docker

> **Onda A** em [[MOC-sprint-a20]]. Lane curta, mecânica, baixo risco — barata
> e desbloqueia [[A20.l1]] (precisa de `python:3.12-slim@sha256:...` para
> garantir paridade entre stages `builder`/`runtime`/`playwright`).

## Status de entrega

**Shipped 2026-05-29** — changelog [[CHG-2026-05-29-A20-L2-SHA-PINNING]].
[[ADR-249]] flipada `Proposto → Decidido`.

**Decisões adotadas (co-design `sre-devops`):**
- **Digest do índice multi-arch** (`docker buildx imagetools inspect ... {{.Manifest.Digest}}`),
  não platform-specific — crítico para dev em Apple Silicon vs CI/prod amd64.
- **Sem auto-merge Docker até L5 (Trivy blocking)** — re-pin de digest do mesmo
  tag não é auditável só pelo diff; até L5, todo bump é review manual.
- **`groups`** no Dependabot separa `docker-security` de `docker-version` por
  diretório (evita ~12 PRs/semana entre os 4 dirs).

**15 refs pinadas:** `python:3.12-slim` (backend `ARG PYTHON_BASE` +
pipeline-service), `node:22-alpine` (frontend ×3, frontend-ops ×3, compose dev),
`postgres:16-alpine` + `redis:7-alpine` (prod/dev/test/smoke). Imagens de build
local (`mathoms-*`) não pinadas. Hook `dev/check_docker_sha_pin.py` verde +
bloqueia casos sintéticos. Build do pipeline-service com base pinada → `whoami`
= `mathoms`.

## Resumo

Pina **todas** as imagens base por digest SHA-256 (`python:3.12-slim`,
`node:22-alpine`, `postgres:16-alpine`, `redis:7-alpine` e quaisquer outras
em `Dockerfile*`/`docker-compose*.yml`). Configura Dependabot
(`package-ecosystem: docker`) com cadência semanal + política de
auto-merge condicionada a CI verde (após [[A20.l5]] mergear Trivy
blocking). Resolve **P0.5**.

## Contexto

Estado atual (`grep -rE 'FROM [a-z]+:[^@]+\s' Dockerfile* pipeline-service/
frontend*/`):

```
Dockerfile:13:                  FROM python:3.12-slim AS base
frontend/Dockerfile:5:          FROM node:22-alpine AS deps
frontend/Dockerfile:24:         FROM node:22-alpine AS builder
frontend/Dockerfile:50:         FROM node:22-alpine AS runner
frontend-ops/Dockerfile:6:      FROM node:22-alpine
pipeline-service/Dockerfile:3:  FROM python:3.12-slim AS base
docker-compose.prod.yml:55:     image: postgres:16-alpine
docker-compose.prod.yml:73:     image: redis:7-alpine
docker-compose.prod.yml:98:     image: redis:7-alpine
```

Zero `@sha256:`. Build no Coolify host hoje pode pegar base diferente da que
rodou em CI ontem — reprodutibilidade = 0. Combinado com [[A20.l10]] (lockfile
Python), fecha o gap completo.

## Escopo IN

- Substitui `FROM <imagem>:<tag>` por `FROM <imagem>:<tag>@sha256:<digest>` em
  todos os Dockerfiles e composes versionados.
- Adiciona `.github/dependabot.yml` com:
  ```yaml
  - package-ecosystem: docker
    directory: "/"
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
  ```
- Configura mesma entry para `pipeline-service/`, `frontend/`, `frontend-ops/`.
- Pre-commit hook `dev/check_docker_sha_pin.py` valida que nenhum Dockerfile
  versionado tem `FROM` sem `@sha256:`.
- Documenta política em [[ADR-249]]: SHA update revisado semanal; security
  patch <72h; auto-merge se CI verde após [[A20.l5]] estiver mergeada.

## Escopo OUT

- Atualizar bases para versões major novas (`python:3.13`, `node:24`) — fora
  de escopo; só pina o que está.
- Pinning de imagens em `_archive/` ou exemplos não-runtime.
- Auto-merge antes de [[A20.l5]] (Trivy blocking) mergear — sem scan, auto-merge
  é arriscado.

## Pré-requisitos

- [[ADR-249]] mergeada como `Proposto`.
- Lista de digests SHA atuais coletada via `docker pull <imagem>:<tag> &&
  docker inspect <imagem>:<tag> | jq '.[0].RepoDigests[0]'`.

## Critério de aceite

1. `grep -rE 'FROM [a-z]+:[^@]+\s' Dockerfile* pipeline-service/Dockerfile
   frontend*/Dockerfile docker-compose*.yml` retorna **0 hits** (nenhuma base
   sem SHA).
2. Pre-commit hook `dev/check_docker_sha_pin.py` registrado em
   `.pre-commit-config.yaml` e verde em `pre-commit run --all-files`.
3. `.github/dependabot.yml` tem entry `docker` em cada diretório com
   `Dockerfile*`.
4. PR de teste do Dependabot (forçado via `gh api ... /dependabot/updates`)
   abre PR de bump em ≤24h após config.
5. Hook bloqueia PR sintético que adiciona `FROM ubuntu:latest` sem SHA.

## Definition of Done

- [x] PR mergeado em `main` com CI verde.
- [x] [[ADR-249]] promovida `Proposto → Decidido (A20.L2)`.
- [x] [[A20.l1]] consome o SHA pinado de `python:3.12-slim` via `ARG
      PYTHON_BASE` (mesmo digest `090ba77e…`, consistência cross-lane).
- [x] Política de auto-merge documentada em [[ADR-249]] — gate temporal
      explícito ligado a [[A20.l5]].
- [x] [CHANGELOG](../../../CHANGELOG.md) entry registrada
      ([[CHG-2026-05-29-A20-L2-SHA-PINNING]]).

## Riscos top 3

1. **Base SHA fica desatualizada rapidamente** — Dependabot resolve, mas se
   Dependabot quebra (config errada), bases ficam vulneráveis. Mitigação:
   monitorar PRs Dependabot semanais; revisão manual em update major.
2. **Multi-arch SHA difere** — Mathoms é só amd64 hoje; risco de regressão se
   alguém tentar build arm64 em macOS Apple Silicon. Mitigação: `docker buildx`
   sempre força `--platform linux/amd64`; documentar em runbook.
3. **Coolify cache stale** — webhook do Coolify pode cachear digest antigo.
   Mitigação: após primeiro deploy pós-A20.L2, forçar `docker pull` no host
   manualmente; runbook deployment.

## Especialista pre-PR

- **`sre-devops`** (obrigatório) — review da política de update Dependabot
  (cadência, auto-merge, escape hatch para CVE crítico).
