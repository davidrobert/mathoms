---
id: ADR-249
type: adr
title: "SHA pinning de imagens base + Dependabot Docker — Sprint A20"
status: Proposto
phase: A20.l2
date: "2026-05-22"
relates_to:
  - "[[ADR-228]]"
  - "[[ADR-230]]"
  - "[[ADR-248]]"
  - "[[ADR-250]]"
  - "[[ADR-251]]"
  - "[[ADR-254]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 249"
  - "SHA pinning Docker"
  - "Dependabot Docker"
tags:
  - type/adr
  - status/proposto
  - area/infra
  - area/docker
  - area/security
  - phase/a20
---

## Contexto

Review independente `sre-devops` (2026-05-22) identificou **P0.5**: todas as
imagens base usadas em Mathoms (`python:3.12-slim`, `node:22-alpine`,
`postgres:16-alpine`, `redis:7-alpine`) usam **tag mutável** — sem
`@sha256:<digest>`. Cada `docker pull` futuro pode pegar uma base diferente
da que rodou em CI ontem, sem rastro em git.

Combinado com **ausência de lockfile Python** ([[ADR-254]] resolve),
reprodutibilidade build = 0. Coolify rebuilda no host CX32 a cada deploy
(prática a sair com [[A20.l4]] / [[ADR-250]]) — risco de regressão de base
upstream entrar em prod silenciosamente.

[[ADR-230]] já mergeada cobriu Trivy filesystem scan; [[ADR-251]] vai cobrir
Trivy image scan blocking. SHA pin é o gate primário — sem ele, scan vira
"tirou foto da imagem deste segundo" sem garantia que a próxima build vê o
mesmo conteúdo.

## Decisão

Pinar **todas** as imagens base por `@sha256:<digest>` em `Dockerfile*` e
`docker-compose*.yml`. Configurar Dependabot (`package-ecosystem: docker`)
com cadência semanal. Política de auto-merge condicionada a CI verde
(incluindo [[A20.l5]] Trivy blocking).

Política de update (operacional):

- **Security patch** (CVE HIGH+): SHA atualizado em <72h.
- **Minor/patch update**: revisão semanal via Dependabot.
- **Major update**: review manual obrigatório (mudança de base implica testes
  de regressão).

Coleta de digest atual via `docker pull <imagem>:<tag> && docker inspect
<imagem>:<tag> | jq '.[0].RepoDigests[0]'`.

Pre-commit hook `dev/check_docker_sha_pin.py` valida que nenhum
`Dockerfile`/`compose` versionado tem `FROM` sem `@sha256:`.

## Alternativas consideradas

### Opção A — SHA pinning manual sem Dependabot

**Rejeitada.** Sem automação, bases ficam stale; security patch demora dias
de processo manual. Aumenta exposição a CVE.

### Opção B — Tag semver (`python:3.12.4-slim`) sem SHA

**Rejeitada.** Mais previsível que `python:3.12-slim` (rolling), mas tag
imutável ainda permite re-tag (upstream pode reconstruir). SHA digest é o
único garante.

### Opção C — Snapshot completo via Docker registry mirror (Harbor)

**Rejeitada.** Operação cara para Mathoms single-host. Vale revisitar quando
multi-region ou compliance regulatório exigir.

### Opção D — SHA pinning + Dependabot (**adotada**)

Cobre todos os gaps: digest imutável + automação de update + revisão policy.
Compatível com fluxo GitHub Actions atual sem dependência externa.

## Consequências

### Positivas

- **P0.5 resolvido** — build determinístico do ponto de partida.
- **CVE em base detectado e patcheado em <72h** com Dependabot.
- **Compatível com [[ADR-248]]** Dockerfile multi-stage (`ARG PYTHON_BASE_SHA`).
- **Compatível com [[ADR-251]]** Trivy image scan blocking (sem SHA pin, scan
  é tiro no escuro).

### Negativas

- **Cadência de PRs Dependabot** — ~3-5 PRs/semana de bump (mitigado por
  auto-merge condicional).
- **PR major bump exige review manual** — ~30min/quarter para revisão.

### Neutras

- **Coolify cache stale** — webhook do Coolify pode cachear digest antigo;
  runbook força `docker pull` no host quando A20.L4 entrega cutover.

## Validação

Critérios em [[A20.l2]] §"Critério de aceite" (5 critérios).

## Migração

Fases em [[A20.l2]] §"Escopo IN":
1. Coletar SHA atuais.
2. Substituir `FROM` em todos os Dockerfiles e composes.
3. Registrar pre-commit hook.
4. Configurar Dependabot.
5. Smoke deploy + validação Coolify.

## Riscos

- **Base SHA fica desatualizada se Dependabot falhar** — monitorar PRs
  semanais; alerta se 14d sem update.
- **Multi-arch SHA difere** — Mathoms só amd64; documenta requisito em runbook.
- **Build cache invalidation em update** — esperado; tolerável dado infrequência.

## Métricas

- 0 `FROM` sem `@sha256:` em código versionado (gate hard).
- Cadência de PRs Dependabot (target ~3-5/semana).
- Mean time to patch CVE HIGH+ (target <72h).

## Referências externas

- [Docker — pinning base images](https://docs.docker.com/build/building/best-practices/#pin-base-image-versions)
- [GitHub Dependabot — Docker ecosystem](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file#package-ecosystem)
