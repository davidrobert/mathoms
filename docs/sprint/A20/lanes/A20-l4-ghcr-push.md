---
id: A20.l4
type: lane
title: "Docker dev↔prod parity — L4 GHCR push em CI + tagging strategy"
sprint: A20
status: open
priority: P0
branch_slug: a20-l4-ghcr-push-tagging
depends_on:
  - "[[A20.l10]]"
parallel_with:
  - "[[A20.l1]]"
  - "[[A20.l7]]"
  - "[[A20.l8]]"
adrs_canonical:
  - "[[ADR-250]]"
tags:
  - type/lane
  - sprint/a20
  - status/ready
  - priority/p0
  - area/infra
  - area/ci
  - area/security
---

# A20.L4 — GHCR push + tagging strategy

> **Onda B** em [[MOC-sprint-a20]] (paralela a [[A20.l1]], [[A20.l7]],
> [[A20.l8]]). **Destrava W4-T02** do [PLATFORM_REVIEW](../../../plan/PLATFORM_REVIEW/_README.md) (`blocked`).
> Resolve **P0.2**.

## Resumo

GH Actions job `release-backend.yml` builda matrix dos 2 targets de [[A20.l1]]
(`runtime` + `playwright`) e publica em `ghcr.io/davidrobert/mathoms-backend:{target}-{sha}`
+ `:{target}-latest`. Coolify webhook atualizado para puxar SHA-tag em vez de
buildar localmente — elimina build no CX32 (~5min CPU 100%/deploy) e habilita
rollback em <60s via `docker pull <sha-anterior>`.

## Contexto

- Owner: `davidrobert` (pessoal). GHCR free tier 50GB suficiente.
- Coolify hoje builda no host CX32 a cada deploy — ~5min CPU 100% degrada
  latência. RTO de rollback >5min (rebuilda imagem anterior).
- Workflows existentes: `.github/workflows/ci.yml`, `security.yml`. Sem
  `deploy.yml` / `release-backend.yml`.
- Build-vs-buy: GHCR escolhido por gratuidade + integração nativa Actions
  (`GITHUB_TOKEN` com `packages: write`) + suporte OCI completo. Alternativas
  (ECR/Docker Hub/Harbor) rejeitadas em [[ADR-250]].

## Decisão de tagging (escopo [[ADR-250]])

Matrix de tags publicadas:

| Evento | Tags aplicadas | Retention |
|---|---|---|
| Push em `main` | `runtime-<sha>`, `playwright-<sha>`, `runtime-main`, `playwright-main` | `<sha>`: indefinido; `main`: sempre aponta release atual |
| Tag `vX.Y.Z` | `runtime-<sha>`, `playwright-<sha>`, `runtime-vX.Y.Z`, `playwright-vX.Y.Z` | indefinido |
| Push em PR `agent/*` ou `feature/*` | `runtime-<sha>`, `playwright-<sha>` | **30 dias** (purge automático) |

**Tags proibidas:** `latest` (anti-padrão — ambíguo, não-reproduzível).

## Workflow proposto

```yaml
# .github/workflows/release-backend.yml
name: release-backend
on:
  push:
    branches: [main]
    tags: ['v*']

permissions:
  contents: read
  packages: write

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target: [runtime, playwright]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ghcr.io/davidrobert/mathoms-backend
          tags: |
            type=ref,event=branch,prefix=${{ matrix.target }}-
            type=ref,event=tag,prefix=${{ matrix.target }}-
            type=sha,prefix=${{ matrix.target }}-,format=long
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile
          target: ${{ matrix.target }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha,scope=${{ matrix.target }}
          cache-to: type=gha,mode=max,scope=${{ matrix.target }}
          provenance: true
          sbom: true
```

## Compose prod referenciando SHA

```yaml
# docker-compose.prod.yml — usar var MATHOMS_SHA via Coolify env
services:
  api:
    image: ghcr.io/davidrobert/mathoms-backend:playwright-${MATHOMS_SHA}
  worker:
    image: ghcr.io/davidrobert/mathoms-backend:runtime-${MATHOMS_SHA}
  beat:
    image: ghcr.io/davidrobert/mathoms-backend:runtime-${MATHOMS_SHA}
```

Coolify webhook expõe `${COMMIT_SHA}` via secret — mapear no entrypoint do
deploy.

## Escopo IN

- `.github/workflows/release-backend.yml` novo workflow.
- Workflow só roda em `push: main` + `push: tags v*` — não roda em todo PR
  (custo CI).
- Retention policy GHCR via GitHub UI ou `gh api`:
  - Untagged: purge >30d
  - `*-pr-*` tags: purge >30d
  - `*-main`, `*-v*`: indefinido
- Runbook `docs/reference/runbooks/coolify_ghcr_deploy.md`:
  - Como Coolify autentica em GHCR (PAT pessoal + Coolify secret)
  - Como fazer cutover do build local → pull GHCR
  - Como rollback (mudar `MATHOMS_SHA` env + redeploy = <60s)
  - Como debugar pull failure (auth, quota, network)
- Smoke deploy em staging contra GHCR antes de cutover prod.
- Atualizar [[ADR-228]] §G3 referenciando A20.L4 como entrega do gate.

## Escopo OUT

- Multi-arch builds (`linux/arm64`).
- Image scan (`trivy image`) — escopo de [[A20.l5]].
- Migrar para `goharbor` self-hosted.
- Cosign signing / SLSA provenance Level 3 — `provenance: true` no workflow é
  suficiente para V1; SLSA L3 é FU.

## Pré-requisitos

- [[ADR-250]] mergeada como `Proposto`.
- [[A20.l10]] mergeada (lockfile existe — Dockerfile multi-stage precisa).
- [[A20.l1]] **em paralelo** — sync de SHA do `Dockerfile` antes de release final.
- GHCR free tier confirmado com `packages: write` token.
- Coolify PAT criado e armazenado em Coolify secrets (não em GH).

## Critério de aceite

1. Primeiro push em `main` pós-merge publica imagens visíveis em
   `https://github.com/davidrobert/mathoms/pkgs/container/mathoms-backend`.
2. `docker pull ghcr.io/davidrobert/mathoms-backend:runtime-<sha>` funciona
   localmente sem login (público) **OU** com PAT (privado — escolha em
   [[ADR-250]]).
3. `docker pull ghcr.io/davidrobert/mathoms-backend:playwright-<sha>` ídem.
4. `gh api /users/davidrobert/packages/container/mathoms-backend/versions |
   jq length` >0 após primeiro merge.
5. Coolify staging recebe nova imagem via pull em <60s (vs ~5min build atual).
6. Runbook documentado e testado por 1 deploy completo em staging.

## Definition of Done

- [ ] PR mergeado em `main` com CI verde.
- [ ] [[ADR-250]] promovida `Proposto → Decidido (A20.L4)`.
- [ ] W4-T02 do [PLATFORM_REVIEW](../../../plan/PLATFORM_REVIEW/_README.md) flippado `blocked → shipped`.
- [ ] Runbook `coolify_ghcr_deploy.md` em `docs/reference/runbooks/`.
- [ ] Staging deployed via GHCR pull (não build local).
- [ ] Prod deployed via GHCR pull pelo menos 1× sem rollback.
- [ ] [[ADR-228]] §G3 atualizada.
- [ ] [CHANGELOG](../../../CHANGELOG.md) entry registrada.

## Riscos top 3

1. **Coolify webhook quebra puxando GHCR (auth, network)** — mitigação: smoke
   deploy em staging antes de cutover; runbook de rollback (voltar para build
   local em emergência).
2. **GHCR quota free tier excedida** — 50GB free para conta pessoal. 2 imagens
   × ~700MB × 30 retention = ~42GB. Margem apertada. Mitigação: configurar
   alerta em 80%; retention agressivo (15d em vez de 30d se necessário).
3. **PAT do Coolify expira** — Mitigação: PAT com expiração >1 ano; alerta no
   calendário 30d antes de expirar.

## Especialistas pre-PR

- **`build-vs-buy`** (obrigatório, blocking) — escolha GHCR vs ECR vs Docker
  Hub vs Harbor via [[ADR-250]]. Briefing: custo (free tier vs pay-per-pull),
  vendor lock-in, integração com Actions, suporte OCI completo.
- **`sre-devops`** (obrigatório, após decisão) — review do workflow +
  retention + runbook + smoke deploy.
- **`senior-cto`** (consultivo) — fecha [[ADR-250]] após build-vs-buy.

## Detalhe operacional

Track prompt em [`../tracks/a20-l4-ghcr-push.md`](../tracks/a20-l4-ghcr-push.md) (criado 2026-05-29; pós-F3/ADR-182 tracks vivem em `docs/sprint/<X>/tracks/`).
