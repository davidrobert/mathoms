---
id: TRACK-a20-l4-ghcr-push
type: track
title: "Track A20.L4 — GHCR push em CI + tagging strategy"
lane: "[[A20.l4]]"
sprint: A20
status: ready
created_at: "2026-05-29"
agent_role: sre-devops
tags:
  - type/track
  - sprint/a20
  - status/ready
  - priority/p0
  - area/infra
  - area/ci
  - area/security
---

# Track A20.L4 — GHCR push + tagging strategy

> **Lane canônica:** [[A20.l4]] (workflow `release-backend.yml` completo, matrix de tags, retention, runbook, critério de aceite).
> · **ADR canônica:** [[ADR-250]] (`Proposto`, GHCR vs ECR/Hub/Harbor).
> · **Branch prefix:** `agent/a20-l4-ghcr-push-tagging/*`
> · **Onda B** — **destrava W4-T02** do [PLATFORM_REVIEW](../../../plan/PLATFORM_REVIEW/_README.md).
>
> ⚠️ **BLOQUEADA POR CONFIRMAÇÃO EXTERNA DO OWNER** — não executável autonomamente. Requer: (1) `packages: write` no `GITHUB_TOKEN` + quota free tier GHCR (50GB) confirmada; (2) PAT do Coolify criado e armazenado em Coolify secrets; (3) Coolify webhook atualizado p/ puxar SHA-tag. Pickup só após o owner confirmar esses 3 pré-requisitos.

## Briefing

Job `release-backend.yml` builda matrix dos 2 targets de [[A20.l1]] (runtime + playwright) e publica em `ghcr.io/davidrobert/mathoms-backend:{target}-{sha}` + `:{target}-main`. Coolify passa a puxar SHA-tag em vez de buildar no CX32 (~5min CPU 100%/deploy → pull <60s; RTO rollback <60s). Resolve P0.2. `latest` é tag **proibida**.

## Pré-flight (documentar no PR — inclui confirmações do owner)

```bash
git fetch origin && git worktree list
ls docs/adr/250-*.md
git log origin/main --oneline | grep -iE 'a20-l1|a20-l10'   # L1+L10 mergeadas
gh api /users/davidrobert/packages?package_type=container 2>/dev/null   # token packages:write
# OWNER confirma: quota GHCR, PAT Coolify, webhook atualizado
```

## Execução (resumo — workflow literal na lane)

1. `.github/workflows/release-backend.yml` (matrix target, `docker/metadata-action`, `provenance: true`, `sbom: true`, cache GHA por target).
2. Roda só em `push: main` + `push: tags v*` (não em todo PR).
3. Retention GHCR: untagged + `*-pr-*` purge >30d; `*-main`/`*-v*` indefinido.
4. `docker-compose.prod.yml` referencia `${MATHOMS_SHA}` por service.
5. Runbook `docs/reference/runbooks/coolify_ghcr_deploy.md` (auth, cutover, rollback <60s, debug pull failure).
6. Smoke deploy staging contra GHCR antes de cutover prod.
7. Atualizar [[ADR-228]] §G3; flip W4-T02 `blocked → shipped` no PLATFORM_REVIEW.

## Especialistas pre-PR

- **`build-vs-buy`** (blocking) — GHCR vs ECR/Hub/Harbor via [[ADR-250]].
- **`sre-devops`** (após decisão) — workflow + retention + runbook + smoke deploy.
- **`senior-cto`** (consultivo) — fecha [[ADR-250]].

## Definition of Done

Ver [[A20.l4]] §"Definition of Done". Resumo: imagens visíveis em GHCR; `docker pull` funciona; staging+prod deployados via pull; [[ADR-250]] `Decidido`; W4-T02 `shipped`; runbook `coolify_ghcr_deploy.md`; [[ADR-228]] §G3.

## Ligações

- **Lane:** [[A20.l4]] · **ADR:** [[ADR-250]] · **Sprint MOC:** [[MOC-sprint-a20]]
- **Upstream:** [[A20.l1]] (targets), [[A20.l10]] (lockfile) · **Downstream:** [[A20.l5]] (Trivy escaneia imagem publicada), [[A20.l9]] (smoke).
