---
id: ADR-249
type: adr
title: "SHA pinning de imagens base + Dependabot Docker — Sprint A20"
status: Decidido
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
  - status/decidido
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

Política de update (operacional · co-design `sre-devops`):

- **Auto-merge — gate temporal:** **nenhum** bump Docker entra por auto-merge
  enquanto [[A20.l5]] (Trivy image scan blocking · [[ADR-251]]) não estiver em
  CI. Razão: re-pin de digest do **mesmo tag** não é auditável só pelo diff —
  a tag é mutável e o digest novo pode trazer CVE novo; sem scan, o digest
  antigo era o auditado, o novo não. Até L5, **todo** bump Docker é review
  manual.
- **Pós-L5:** auto-merge apenas para `version-update:semver-patch` + `digest`,
  e somente se o Trivy retornar **0 HIGH/CRITICAL** no PR. Minor/major sempre
  manual.
- **Security patch** (CVE HIGH+): escape hatch <72h — PR manual com label
  `security` + auto-merge, sem esperar a cadência semanal. Grupo
  `docker-security` (`applies-to: security-updates`) separado do
  `docker-version` para cadência/SLA distintos.
- **Cadência version-updates:** semanal (segunda 06:00 BRT), agrupada por
  diretório (`groups` evita até ~12 PRs/semana entre os 4 diretórios).

Digest = **índice multi-arch** (manifest list), não platform-specific —
crítico para dev em Apple Silicon (arm64) com CI/prod amd64. Coleta:

```
docker buildx imagetools inspect <imagem>:<tag> --format '{{.Manifest.Digest}}'
```

`docker inspect ... RepoDigests[0]` retorna o mesmo digest quando a tag é uma
manifest list, mas `buildx imagetools` é a fonte inequívoca. Forma do pin:
`FROM <img>:<tag>@sha256:<digest>` (tag preservada por legibilidade).

Pre-commit hook `dev/check_docker_sha_pin.py` valida que nenhum
`Dockerfile`/`compose` versionado tem `FROM`/`image:` externo sem `@sha256:`
(isenta stage refs, `scratch` e imagens de build local `mathoms-*`).

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

### Notas de entrega — L2 (2026-05-29)

Implementado e validado:

- **15 refs pinadas** por digest do índice multi-arch: `python:3.12-slim`
  (backend `ARG PYTHON_BASE` + `pipeline-service/Dockerfile`), `node:22-alpine`
  (frontend ×3 + frontend-ops ×3 + `docker-compose.dev.yml`),
  `postgres:16-alpine` + `redis:7-alpine` (prod/dev/test/smoke composes).
- **Imagens de build local** (`mathoms-backend:*`, `mathoms-frontend*:*`)
  **não** pinadas — `image:` ali é o nome do artefato buildado, não base.
- **`pipeline-service/docker-compose.yml` não existe** (a tabela D2 de
  [[ADR-252]] o listava como "MANTER", mas o arquivo nunca existiu) → entry
  Dependabot `/pipeline-service` cobre só o Dockerfile.
- **Hook `dev/check_docker_sha_pin.py`** registrado em `.pre-commit-config.yaml`;
  verde em todos os 4 Dockerfiles + 4 composes; bloqueia `FROM ubuntu:latest`
  e `image: alpine:3.20` sintéticos (critério 5). Escaneia `image:` em compose
  além de `FROM`, e valida o default do `ARG` quando `FROM ${ARG}` o referencia.
- **Build verificado** — `pipeline-service` builda com a base pinada,
  `whoami` → `mathoms`. Digest `090ba77e…` do `python:3.12-slim` é o mesmo já
  consumido por [[A20.l1]] (ADR-248), confirmando consistência cross-lane.
- **Critério 4 deferido** — forçar PR sintético do Dependabot via
  `gh api .../dependabot/updates` exige a config já em `main` + janela de
  scan do GitHub; verificável só pós-merge (gate humano/observação, não
  bloqueia a lane).

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
