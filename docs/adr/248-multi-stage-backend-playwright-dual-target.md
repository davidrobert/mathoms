---
id: ADR-248
type: adr
title: "Multi-stage backend Dockerfile com dual target (runtime / playwright) — Sprint A20"
status: Proposto
phase: A20.l1
date: "2026-05-22"
relates_to:
  - "[[ADR-076]]"
  - "[[ADR-111]]"
  - "[[ADR-129]]"
  - "[[ADR-228]]"
  - "[[ADR-230]]"
  - "[[ADR-249]]"
  - "[[ADR-250]]"
  - "[[ADR-253]]"
  - "[[ADR-254]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 248"
  - "Multi-stage backend"
  - "Playwright dual target"
  - "Docker runtime playwright"
tags:
  - type/adr
  - status/proposto
  - area/infra
  - area/docker
  - area/devops
  - phase/a20
---

## Contexto

Review independente do `sre-devops` (2026-05-22) classificou maturidade Docker
do Mathoms em **2.5/5** ("funcional para staging single-host, frágil para
produção"). Dois findings P0 endereçam o `Dockerfile` backend único:

- **P0.1 — Playwright/Chromium ausente em runtime.** `backend/requirements.txt`
  declara `playwright>=1.47.0`; [`backend/app/services/pdf_renderer.py`](../../backend/app/services/pdf_renderer.py)
  exige Chromium para renderizar PDF server-side ([[ADR-076]] / [[ADR-129]]).
  Mas nenhum Dockerfile faz `playwright install chromium --with-deps`. Em prod,
  qualquer chamada de `/reports/{id}/pdf` cai no `_check_playwright()` que loga
  `WARNING` e retorna `None`. **Feature está quebrada por construção em
  produção.**
- **P0.3 — `build-essential` em runtime.** [`Dockerfile`](../../Dockerfile)
  atual é single-stage. Instala `build-essential libpq-dev curl python3-dev`
  (linhas 17-22) e **nunca remove**. Imagem final carrega GCC, dpkg-dev,
  headers — ~700MB extra + superfície de ataque enorme em runtime. Wheels
  pré-built (`psycopg2-binary`, `cryptography`, `asyncpg`) cobrem 99% dos
  casos x86_64 manylinux; toolchain só serve fallback ARM exótico.

Adicionalmente, há um **problema arquitetural** que P0.1 escancara: `api`
precisa de Playwright (export PDF), mas `worker` e `beat` não — hoje
`docker-compose.prod.yml:127-160` referencia a mesma tag para todos os
services. Quando Playwright + Chromium for instalado, **3 containers carregam
~600MB de Chromium morto** (worker e beat nunca renderizam PDF). Em Hetzner
CX32 (4 vCPU / 8GB RAM), isso são ~450MB de RAM desperdiçada onde já apertava.

A decisão precisa endereçar simultaneamente: (a) Playwright instalado e
funcional; (b) toolchain de build fora de runtime; (c) imagem enxuta para
worker/beat sem perder funcionalidade do api; (d) compatibilidade com SHA
pinning ([[ADR-249]]) e lockfile com hashes ([[ADR-254]]); (e) cache de
layers eficiente para CI.

## Decisão

Adotar **Dockerfile multi-stage com dual target** (Opção C — ver alternativas
abaixo):

- **3 stages:** `builder` → `runtime` → `playwright`
- **2 targets publicáveis:** `runtime` (worker/beat, <450MB) e `playwright`
  (api, <950MB)
- **`playwright` herda de `runtime`** via `FROM runtime AS playwright` — drift
  impossível por construção; ambos compartilham mesma layer Python + deps
- **Compose prod escolhe target por service:**
  - `api → ghcr.io/davidrobert/mathoms-backend:playwright-<sha>`
  - `worker, beat → ghcr.io/davidrobert/mathoms-backend:runtime-<sha>`
- **Default target = `playwright`** (build sem `--target` produz superset
  seguro) — dev local sem flag pega imagem completa.
- **2 pushes ao GHCR por release** (`runtime-<sha>` + `playwright-<sha>`),
  matrix build no workflow `release-backend.yml` ([[A20.l4]] / [[ADR-250]]).
- **Builder stage** instala `build-essential libpq-dev`, constrói wheels em
  `/wheels/`, depois é descartado. Runtime instala apenas via `pip install
  --no-index --find-links /wheels` (zero compile, determinístico).
- **Runtime stage** instala apenas runtime libs: `libpq5` (fallback psycopg
  até [[ADR-253]] consolidar driver) + `curl` (healthcheck). User não-root
  (UID 1000) preservado.
- **Playwright stage** instala libs sistema (`libnss3`, `libatk-bridge2.0-0`,
  `libxkbcommon0`, `libcups2`, `libdrm2`, `libgbm1`, `libasound2`,
  `libpango-1.0-0`, `libcairo2`, `libatspi2.0-0`, `fonts-liberation` e
  correlatos), depois `python -m playwright install chromium` como user
  `mathoms`. Browsers ficam em `/home/mathoms/.cache/ms-playwright/`.

Snippet completo do Dockerfile em [[A20.l1]] §"Dockerfile multi-stage".

## Alternativas consideradas

### Opção A — Dockerfiles separados (`backend.Dockerfile` + `backend-playwright.Dockerfile`)

**Rejeitada.** Cada Dockerfile teria sua própria sequência de `pip install`
— deps Python podem divergir silenciosamente entre os dois entre commits.
Drift é detectável só em runtime, depois de deploy. Custo CI: 2 builds
completos sem compartilhar layer base. Refactor "mover PDF render pro worker"
amanhã exigiria mexer em 2 Dockerfiles.

### Opção B — Imagem única com Chromium (status quo + Playwright)

**Rejeitada.** Mantém simplicidade do compose (um único `image:` para
todos os services). Mas `worker` e `beat` carregam Chromium permanentemente:
~150MB RES por container × 3 = ~450MB RAM desperdiçados em CX32 (4 vCPU /
8GB). Combinado com `build-essential` ficando em runtime se mantivermos
single-stage, viraria imagem ~1.1GB+. Anti-FinOps e anti-segurança (Chromium
tem CVE history não-trivial — Trivy reportaria em todo container, mesmo onde
não é usado).

### Opção C — Dual target no mesmo Dockerfile (**adotada**)

`FROM runtime AS playwright` — `playwright` é literalmente `runtime` +
camada Chromium. Drift impossível (mesma layer base por construção). Cache
GHA compartilhado nos stages comuns. Refactor amanhã: troca `image:` do
service, zero mudança no Dockerfile. Custo: 2 pushes/release no GHCR (~+850MB
storage por SHA, mitigado por retention de 30d em PR-SHA — [[ADR-250]]).

## Consequências

### Positivas

- **P0.1 resolvido** — PDF render funciona end-to-end em prod (target
  `playwright`).
- **P0.3 resolvido** — `build-essential` sai de runtime; toolchain só vive
  em stage descartado.
- **~60% redução** no tamanho da imagem `runtime` (~1.1GB → <450MB), ~450MB
  de RAM economizados em CX32 (worker + beat sem Chromium).
- **Superfície de ataque menor** em worker/beat (sem Chromium); Trivy
  ([[ADR-251]]) escaneia apenas o que cada container realmente usa.
- **Cache GHA eficiente** — rebuild de PR que só toca `backend/app/api/*.py`
  reaproveita layers de build + install Python + Chromium. Build CI <2min
  warm.
- **Determinismo** quando combinado com SHA pin ([[ADR-249]]) e lockfile
  ([[ADR-254]]) — builds idênticos em runners diferentes.
- **Compatibilidade com stateless rigoroso** ([[ADR-111]]) — runtime sem
  state mutável; user non-root preservado.

### Negativas

- **Operações via compose ficam mais complexas:** `image:` diferente por
  service em prod; documentação em [[A20.l1]] §"Compose prod por service"
  obrigatória.
- **2 pushes/release no GHCR** — storage ~2× (mitigado por retention).
- **Build time ligeiramente maior** — matrix build sequencial em
  `release-backend.yml` (cache compartilhado reduz a ~+1min vs build único).
- **Risco de regressão** quando alguém alterar `Dockerfile` sem entender
  que `runtime` é base do `playwright` — comentário inline + runbook
  `docs/reference/runbooks/docker_images.md` mitigam.

### Neutras

- **PDF render permanece em `api`** (não migra pra Celery agora) — Opção C
  preserva opcionalidade: se virar Celery task pesada, troca `image:` do
  worker pra `playwright-<sha>` sem mudar Dockerfile.
- **Multi-arch** (`linux/arm64`) continua non-goal — Opção C é compatível
  quando virar prioridade.

## Validação

Critérios em [[A20.l1]] §"Critério de aceite" (10 critérios). Resumo:

1. `docker build --target runtime` produz imagem <450MB.
2. `docker build --target playwright` produz imagem <950MB.
3. Smoke render PDF retorna `application/pdf` >50KB.
4. **Audit worker enxuto:** `ps -ef | grep chromium` em container `runtime`
   retorna vazio.
5. Heredity check: `docker history` mostra layers de `runtime` antes de
   Chromium.
6. CI matrix builda ambos os targets em ≤6min com cache quente.

## Migração

Sequência de Onda B em [[MOC-sprint-a20]]:

1. [[A20.l10]] mergeada (lockfile com hashes em `main`).
2. [[A20.l2]] mergeada (SHA pin de `python:3.12-slim`).
3. [[A20.l1]] (esta ADR) abre PR com Dockerfile refatorado + smoke local.
4. [[A20.l4]] em paralelo prepara `release-backend.yml` com matrix build.
5. PRs de L1 + L4 mergeiam no mesmo dia → primeiro push ao GHCR de imagens
   versionadas.
6. Coolify webhook atualizado para puxar tag SHA (runbook em
   `docs/reference/runbooks/coolify_ghcr_deploy.md`).
7. Staging recebe pull manual primeiro; prod recebe após smoke verde.

## Riscos

- **Wheels nativos diferentes entre `builder` e `runtime`** — mitigado por
  SHA pin idêntico em ambos stages ([[ADR-249]]).
- **Chromium libs faltando em runtime stage** (ex.: `libatspi2.0-0`) —
  mitigado por smoke render de relatório completo (não trivial `<html>Hello</html>`).
- **Cache GHA cross-target invalidando** — mitigado por `scope=${target}`
  no `cache-to`.

## Métricas

Ver [[A20.l1]] §"Métricas" e [[MOC-sprint-a20]] §"Métricas de saúde do sprint".

## Referências externas

- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Playwright Docker docs](https://playwright.dev/python/docs/docker)
- [GitHub Actions Docker cache](https://docs.docker.com/build/cache/backends/gha/)
