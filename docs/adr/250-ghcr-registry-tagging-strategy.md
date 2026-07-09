---
id: ADR-250
type: adr
title: "GHCR como registry de imagens + tagging strategy — Sprint A20"
status: Proposto
phase: A20.l4
date: "2026-05-22"
relates_to:
  - "[[ADR-228]]"
  - "[[ADR-230]]"
  - "[[ADR-248]]"
  - "[[ADR-249]]"
  - "[[ADR-251]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 250"
  - "GHCR registry"
  - "Docker tagging strategy"
tags:
  - type/adr
  - status/proposto
  - area/infra
  - area/ci
  - area/security
  - phase/a20
---

## Contexto

Review independente `sre-devops` (2026-05-22) identificou **P0.2**: Coolify
hoje **builda imagens no host CX32** a cada deploy. Implicações:

- ~5min de CPU 100% no host de prod por deploy, degradando latência ativa.
- Rollback "rebuilda imagem anterior" → RTO >5min (não cumpre meta SLO).
- Sem registry, `trivy image` scan ([[ADR-251]]) é impossível — não há
  imagem pinável para escanear.
- Drift entre dev e prod: `apt update` upstream pode quebrar prod
  silenciosamente.

W4-T02 do [PLATFORM_REVIEW](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) reconhece o gap (`blocked` há semanas).

A decisão precisa endereçar: (a) registry escolhido com trade-off de custo/
lock-in/integração; (b) política de tagging que garante imutabilidade e
rollback; (c) política de retention; (d) integração com Coolify sem
quebrar fluxo de deploy.

## Decisão

**Adotar GitHub Container Registry (GHCR)** como registry primário:

- Repo: `ghcr.io/davidrobert/mathoms-backend`.
- Workflow `release-backend.yml` em GH Actions builda matrix dos 2 targets
  ([[ADR-248]]) e pusha em push em `main` + tag `v*`.
- Coolify webhook atualizado para `docker pull` em vez de `docker build`
  local.

**Tagging strategy:**

| Evento | Tags |
|---|---|
| Push em `main` | `runtime-<sha>`, `playwright-<sha>`, `runtime-main`, `playwright-main` |
| Tag `vX.Y.Z` | `runtime-<sha>`, `playwright-<sha>`, `runtime-vX.Y.Z`, `playwright-vX.Y.Z` |
| Push em PR `agent/*`/`feature/*` | `runtime-<sha>`, `playwright-<sha>` (retention 30d) |

**Tags proibidas:** `latest` — anti-padrão (ambíguo, não-reproduzível).

**Retention:**

- `<sha>` em PR branches: **30 dias** (purge automático via GHCR)
- `<sha>` em `main`/`v*`: indefinido
- `runtime-main`/`playwright-main`: sempre aponta release atual

Imagens publicadas com `provenance: true` (SLSA Level 2) e `sbom: true`.
[[ADR-251]] adiciona Trivy blocking + SBOM CycloneDX em CI.

## Alternativas consideradas

### Opção A — Amazon ECR

**Rejeitada.** Custo: storage $0.10/GB-mês + transferência. Para 50GB
estimados em 30d retention, ~$5-10/mês — pequeno mas não-zero, contra
GHCR free tier (50GB inclusos no plano pessoal). Vendor lock-in AWS sem
benefício compensador (Mathoms não usa outros serviços AWS).

### Opção B — Docker Hub

**Rejeitada.** Rate limit em pull anonymous (100/6h IP) compatível com dev
local mas frágil em CI runner pool. Plano paid ($7/mês para Pro) corrige
mas é custo recorrente. Histórico de instabilidade em 2020-2023.

### Opção C — Self-hosted Harbor

**Rejeitada para V1.** Operação cara (precisa Postgres + Redis + storage
extra no CX32 já apertado). Vale revisitar se multi-region ou compliance
regulatório exigir. Adiciona ponto de falha.

### Opção D — GHCR (**adotada**)

- **Custo:** $0 free tier (50GB) — suficiente.
- **Integração:** nativa com GitHub Actions (`GITHUB_TOKEN` com
  `packages: write`).
- **Lock-in:** mínimo — GHCR é OCI standard; export trivial.
- **Latência:** baixa (CDN GitHub Edge).
- **Suporte:** Coolify suporta GHCR via Personal Access Token.

## Consequências

### Positivas

- **P0.2 resolvido** — Coolify não builda mais no host CX32.
- **Rollback em <60s** via `docker pull <sha-anterior>` + `docker-compose up`.
- **W4-T02** do [PLATFORM_REVIEW](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) flippa `blocked → shipped`.
- **Trivy image scan habilitado** ([[ADR-251]]).
- **Auditabilidade:** cada release tem SHA + provenance + SBOM publicados.
- **Build em runner CI** dedicado (não host de prod) — paraleliza com testes.

### Negativas

- **Coolify webhook precisa atualizar** — passo manual em [[A20.l4]]; runbook
  obrigatório.
- **GHCR quota free tier (50GB) é apertada** — 2 imagens × ~700MB × 30 dias
  retention = ~42GB. Margem ~16% para cold/release tags. Mitigação: alerta
  em 80%; retention agressivo (15d se necessário).
- **PAT do Coolify expira** — gestão de credencial.

### Neutras

- **Provenance + SBOM publicados** — overhead ~+5s/build, ganho compliance.

## Validação

Critérios em [[A20.l4]] §"Critério de aceite" (6 critérios).

## Migração

Fases em [[A20.l4]] §"Escopo IN":
1. Workflow `release-backend.yml` mergeado em `main`.
2. Primeiro push pós-merge publica imagens visíveis em GHCR.
3. Coolify staging recebe imagem via pull.
4. Smoke deploy verde.
5. Coolify prod recebe imagem via pull.
6. W4-T02 flippado.

## Riscos

- **Coolify webhook quebra** — runbook de rollback (voltar para build local
  em emergência).
- **GHCR quota excedida** — alerta + retention agressivo.
- **PAT Coolify expira** — alerta calendário 30d antes.

## Métricas

- Deploy time (target <60s para `docker pull` + restart vs ~5min build atual).
- Rollback time (target <60s).
- GHCR storage usage (target <80% free tier).
- Provenance + SBOM artifact size (target <1MB cada).

## Referências externas

- [GHCR docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker metadata-action](https://github.com/docker/metadata-action)
- [Coolify + GHCR deployment](https://coolify.io/docs/applications/private-image)
