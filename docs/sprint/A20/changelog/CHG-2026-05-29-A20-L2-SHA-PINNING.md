---
id: CHG-2026-05-29-A20-L2-SHA-PINNING
type: changelog-entry
date: "2026-05-29"
sprint: A20
lane: "[[A20.l2]]"
adrs: ["[[ADR-249]]"]
summary: |
  A20.L2 — SHA pinning de todas as bases por digest do índice multi-arch
  (P0.5) + Dependabot Docker. 15 refs pinadas (python/node/postgres/redis)
  por @sha256 do manifest list (não platform-specific — Apple Silicon dev vs
  amd64 CI/prod). Hook `dev/check_docker_sha_pin.py` bloqueia FROM/image sem
  pin. Dependabot ganha 4 entries docker com groups security/version; sem
  auto-merge Docker até L5 (Trivy blocking) entrar em CI.
tags:
  - type/changelog-entry
  - sprint/a20
  - area/infra
  - area/docker
  - area/security
---

# A20.L2 — SHA pinning de bases + Dependabot Docker

- **15 refs pinadas por digest do índice multi-arch** ([[ADR-249]] · resolve
  **P0.5**): toda imagem base externa em `Dockerfile*` e `docker-compose*.yml`
  ganha `@sha256:<digest>`. Digest = **manifest list** (índice multi-arch) via
  `docker buildx imagetools inspect <img>:<tag> --format '{{.Manifest.Digest}}'`,
  **não** platform-specific — crítico para dev em Apple Silicon (arm64) vs
  CI/prod amd64.
  - `python:3.12-slim@sha256:090ba77e…` — backend (`ARG PYTHON_BASE`) +
    `pipeline-service/Dockerfile`. Mesmo digest já consumido por [[A20.l1]]
    (ADR-248), confirmando consistência cross-lane.
  - `node:22-alpine@sha256:968df39a…` — frontend ×3 (deps/builder/runner),
    frontend-ops ×3, `docker-compose.dev.yml`.
  - `postgres:16-alpine@sha256:16bc17c6…` + `redis:7-alpine@sha256:6ab0b6e7…`
    — composes prod/dev/test/smoke.
  - **Imagens de build local** (`mathoms-backend:*`, `mathoms-frontend*:*`)
    **não** pinadas — `image:` ali é o nome do artefato buildado, não base.
- **Hook `dev/check_docker_sha_pin.py`** registrado em `.pre-commit-config.yaml`:
  falha (exit 1) se qualquer base externa não tiver `@sha256:`. Escaneia `FROM`
  em Dockerfiles (isenta stage refs, `scratch`, e valida o default do `ARG`
  quando `FROM ${ARG}` o referencia) **e** `image:` em composes (isenta
  `mathoms-*` local). Verde nos 4 Dockerfiles + 4 composes; bloqueia
  `FROM ubuntu:latest` e `image: alpine:3.20` sintéticos (critério 5).
- **Dependabot Docker** ([[ADR-249]]): 4 entries `package-ecosystem: docker`
  (`/`, `/pipeline-service`, `/frontend`, `/frontend-ops`), cadência semanal
  (segunda 06:00 BRT), `groups` separa `docker-security`
  (`applies-to: security-updates`) de `docker-version`
  (`applies-to: version-updates`) — cadência/SLA distintos, evita ~12
  PRs/semana entre os 4 diretórios.
- **Política de auto-merge — gate temporal** (co-design `sre-devops`):
  **nenhum** bump Docker entra por auto-merge enquanto [[A20.l5]] (Trivy image
  scan blocking · [[ADR-251]]) não estiver em CI. Razão: re-pin de digest do
  **mesmo tag** não é auditável só pelo diff — a tag é mutável e o digest novo
  pode trazer CVE novo. Pós-L5: auto-merge só para `version-update:semver-patch`
  + `digest` com Trivy retornando 0 HIGH/CRITICAL. Security patch (CVE HIGH+):
  escape hatch <72h via label `security`.

## Verificação

- **Critério 1** — `grep -rE 'FROM [a-z]+:[^@]+\s'` em Dockerfiles + composes
  retorna **0 hits** (nenhuma base sem SHA).
- **Critério 2** — `dev/check_docker_sha_pin.py` registrado e verde em
  `pre-commit run`.
- **Critério 3** — `.github/dependabot.yml` tem entry `docker` em cada
  diretório com `Dockerfile*` (4 entries; total 8 updates no arquivo).
- **Critério 5** — hook bloqueia PR sintético com `FROM ubuntu:latest` e
  `image: alpine:3.20` sem pin.
- **Build** — `pipeline-service` builda com a base pinada (`docker build -f
  pipeline-service/Dockerfile .`), `whoami` → `mathoms`.
- **Critério 4 deferido** — forçar PR sintético do Dependabot via
  `gh api .../dependabot/updates` exige a config já em `main` + janela de scan
  do GitHub; verificável só pós-merge (gate humano/observação, não bloqueia a
  lane).

[[ADR-249]] flipada `Proposto → Decidido`. Lane [[A20.l2]] `open → shipped`.
