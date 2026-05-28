---
id: A20.l1
type: lane
title: "Docker dev↔prod parity — L1 Multi-stage backend + Playwright dual target"
sprint: A20
status: open
priority: P0
branch_slug: a20-l1-backend-multistage
depends_on:
  - "[[A20.l10]]"
parallel_with:
  - "[[A20.l4]]"
  - "[[A20.l7]]"
  - "[[A20.l8]]"
adrs_canonical:
  - "[[ADR-248]]"
tags:
  - type/lane
  - sprint/a20
  - status/ready
  - priority/p0
  - area/infra
  - area/docker
  - area/devops
---

# A20.L1 — Multi-stage backend + Playwright dual target

> **Onda B** em [[MOC-sprint-a20]] (paralela a [[A20.l4]], [[A20.l7]], [[A20.l8]]).
> Lane gateway: refatora o `Dockerfile` único atual (single-stage `python:3.12-slim`,
> 60 linhas, ~1.1GB) em **3 stages** com **2 targets publicáveis** (`runtime`
> enxuto + `playwright` com Chromium). Resolve o problema arquitetural de
> **api precisa de Playwright** (export PDF via [[ADR-076]]) **mas worker/beat
> não** — hoje todos carregam ~600MB de Chromium morto (que sequer está instalado,
> P0.1).

## Objetivo

Materializar [[ADR-248]] (Opção C — dual target no mesmo Dockerfile). Um único
build context, três stages (`builder` → `runtime` → `playwright`), dois targets
publicados ao GHCR por release (`runtime-<sha>` e `playwright-<sha>`).
`docker-compose.prod.yml` referencia tags diferentes por service:

- `api` → `mathoms-backend:playwright-<sha>` (~900MB com Chromium)
- `worker`, `beat` → `mathoms-backend:runtime-<sha>` (~450MB enxuto)

`playwright` stage **herda 100%** do `runtime` (`FROM runtime AS playwright`),
só adiciona camada Chromium. Garante que worker rodando target `runtime`
**nunca** tem processos `node`/`chromium` no container — auditável via `ps -ef`
no smoke test.

## Por que Opção C (não A, não B)

Decidida em [[ADR-248]]:

| Opção | Imagens publicadas | Risco de drift | Custo CI | Veredito |
|---|---|---|---|---|
| A — Dockerfiles separados | 2 (`backend.Dockerfile`, `backend-playwright.Dockerfile`) | Alto — deps Python divergem silenciosamente | 2 builds completos | Rejeitada |
| B — Imagem única (status quo) | 1 (~1.1GB todos os services) | Zero, mas worker carrega 600MB morto | 1 build | Rejeitada (anti-FinOps) |
| **C — Dual target, 1 Dockerfile** | 2 (`runtime-<sha>`, `playwright-<sha>`) | Zero — `playwright` herda de `runtime` por construção | 1 build com 2 `--target` (cache compartilhado) | **Adotada** |

## Dockerfile multi-stage (3 stages)

```dockerfile
# syntax=docker/dockerfile:1.7
# ADR-248 — multi-stage backend com dual target (runtime / playwright).
# Build:
#   docker build --target runtime    -t mathoms-backend:runtime-<sha>    .
#   docker build --target playwright -t mathoms-backend:playwright-<sha> .
# Default target = playwright (superset seguro pra dev local rodar tudo).

# ──────────────────────────────────────────────────────────────────────────
# Stage 1: builder — compila wheels nativos (cryptography, asyncpg, etc.)
# Descartado no resultado final; só produz wheels em /wheels/.
# ──────────────────────────────────────────────────────────────────────────
ARG PYTHON_BASE_SHA=sha256:TBD_PIN_L2  # SHA pin enforced em L2 (ADR-249)
FROM python:3.12-slim@${PYTHON_BASE_SHA} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Lockfile L10 (ADR-254) substitui requirements.txt sem hashes — copia já com hashes.
# Ordering: requirements primeiro pra maximizar cache layer.
COPY requirements.lock /build/requirements.lock
COPY backend/requirements.lock /build/backend/requirements.lock

# Constroi wheels em /wheels/ — instala depois em runtime stage.
RUN pip wheel --require-hashes --wheel-dir /wheels \
        -r /build/requirements.lock \
        -r /build/backend/requirements.lock

# ──────────────────────────────────────────────────────────────────────────
# Stage 2: runtime — base enxuta (api fora-de-Playwright, worker, beat).
# Target publicado: mathoms-backend:runtime-<sha>
# Tamanho alvo: <450MB.
# ──────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim@${PYTHON_BASE_SHA} AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    MATHOMS_LOG_FORMAT=json

# Apt deps de runtime (sem build-essential): libpq5 pro psycopg fallback, curl pro healthcheck.
# L8/ADR-253 consolida driver — quando entregue, libpq5 pode sair se asyncpg-only.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# User não-root (UID 1000) — mesmo padrão do legado single-stage.
RUN useradd --create-home --shell /bin/bash --uid 1000 mathoms

WORKDIR /app

# Instala wheels do builder — zero compile, fast, deterministic.
COPY --from=builder /wheels /wheels
COPY requirements.lock /app/requirements.lock
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --require-hashes --no-index --find-links /wheels \
        -r /app/requirements.lock \
        -r /app/backend/requirements.lock \
    && rm -rf /wheels

# Código — ordenado pra cache (config muda menos que código).
COPY config/ /app/config/
COPY pipeline/ /app/pipeline/
COPY backend/ /app/backend/
COPY pyproject.toml /app/pyproject.toml

RUN mkdir -p /app/storage \
    && chmod +x /app/backend/scripts/entrypoint.sh \
    && chown -R mathoms:mathoms /app

USER mathoms
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/backend/scripts/entrypoint.sh"]
CMD ["api"]

# ──────────────────────────────────────────────────────────────────────────
# Stage 3: playwright — runtime + Chromium + libs.
# Herda 100% de runtime; só adiciona camada Chromium via playwright install.
# Target publicado: mathoms-backend:playwright-<sha>
# Tamanho alvo: <950MB.
# DEFAULT TARGET (superset seguro pra dev).
# ──────────────────────────────────────────────────────────────────────────
FROM runtime AS playwright

USER root

# Libs Chromium em Debian bookworm (slim).
# Lista validada via `playwright install-deps chromium --dry-run` e enxugada — só
# o necessário pro PDF rendering headless server-side em backend/app/services/pdf_renderer.py.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libnss3 \
        libnspr4 \
        libdbus-1-3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libcairo2 \
        libatspi2.0-0 \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

USER mathoms

# Instala apenas Chromium (não webkit/firefox) — única engine usada pelo pdf_renderer.
# Browsers ficam em /home/mathoms/.cache/ms-playwright/ (já owned pelo user).
RUN python -m playwright install chromium
```

## Compose prod por service

```yaml
# docker-compose.prod.yml — extrato relevante (ADR-248)
# ${MATHOMS_SHA} resolvido pelo CI ou pelo entrypoint do operador.

services:
  api:
    image: ghcr.io/davidrobert/mathoms-backend:playwright-${MATHOMS_SHA}
    # PDF export precisa de Chromium — playwright target obrigatório.
    command: api
    # ... resto config

  worker:
    image: ghcr.io/davidrobert/mathoms-backend:runtime-${MATHOMS_SHA}
    # Celery worker NÃO renderiza PDF (PDF render é endpoint síncrono em api).
    # Runtime target enxuto; valida via smoke `docker exec worker ps -ef | grep -i chromium` → vazio.
    command: worker

  beat:
    image: ghcr.io/davidrobert/mathoms-backend:runtime-${MATHOMS_SHA}
    # Scheduler puro — nunca renderiza nada.
    command: beat
```

## Workflow GHCR (matrix build dos 2 targets)

Definido em detalhe em [[A20.l4]] / [[ADR-250]]; snippet para coordenação:

```yaml
# .github/workflows/release-backend.yml (extrato)
name: release-backend
on:
  push:
    tags: ['v*']

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
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile
          target: ${{ matrix.target }}
          push: true
          # Tags duplas: target-sha (imutável) + target-latest (aponta release atual).
          tags: |
            ghcr.io/davidrobert/mathoms-backend:${{ matrix.target }}-${{ github.sha }}
            ghcr.io/davidrobert/mathoms-backend:${{ matrix.target }}-latest
          cache-from: type=gha,scope=${{ matrix.target }}
          cache-to: type=gha,mode=max,scope=${{ matrix.target }}
```

Cache GHA escopado por target — `runtime` e `playwright` compartilham layers de
`builder` e `runtime` automaticamente porque o stage `playwright` é `FROM runtime`,
mas o cache do BuildKit é por target para evitar invalidação cruzada.

## Estratégia de cache de layers

Ordem de `COPY` no Dockerfile maximiza cache hit:

1. `requirements.lock` (muda raramente — só em update de deps via [[A20.l10]])
2. `pip wheel ...` (idêntico se #1 idêntico)
3. `pip install --no-index ...` (idêntico se wheels idênticos)
4. `config/` (schemas + report_layout — muda quando produto evolui)
5. `pipeline/` (muda em features de domínio)
6. `backend/` (muda mais frequente — code da API)
7. `playwright install chromium` (só roda se base `runtime` invalidou)

Rebuild de PR que só toca `backend/app/api/*.py` reaproveita layers 1-5 — build
local <30s, build CI <2min com cache GHA quente.

## Critério de aceite

1. `docker build --target runtime -t mathoms-backend:runtime-test .` produz
   imagem com `docker image inspect --format '{{.Size}}'` < **450 MB**.
2. `docker build --target playwright -t mathoms-backend:playwright-test .`
   produz imagem < **950 MB**.
3. `docker run --rm mathoms-backend:playwright-test python -m playwright --version`
   imprime versão correta sem stack trace.
4. **Smoke render PDF:** `docker run -d --name smoke mathoms-backend:playwright-test
   api`, então `curl -X POST http://localhost:8000/v1/reports/<id>/pdf` retorna
   `200` com `application/pdf` — fixture sintética, sem PII.
5. **Audit worker enxuto:** `docker run --rm mathoms-backend:runtime-test worker`
   arranca; `docker exec smoke-worker ps -ef | grep -iE '(chromium|chrome|node)'`
   retorna **vazio** (exit code 1 do `grep`).
6. Heredity check: `docker history mathoms-backend:playwright-test` mostra as
   layers de `runtime` antes da layer Chromium (prova `FROM runtime AS playwright`).
7. Pre-commit `hadolint` verde no Dockerfile (depois de SHA pin em
   [[A20.l2]]/[[ADR-249]]).
8. `requirements.lock` existe e é consumido (depende de [[A20.l10]] /
   [[ADR-254]]).
9. Build sem `--target` (default) produz imagem `playwright` — verificado por
   `docker image inspect $(docker build -q .) --format '{{.Size}}'` > 800 MB.
10. CI matrix ([[A20.l4]]) builda ambos os targets em ≤6min total com cache
    quente (medido em 3 runs consecutivos do mesmo SHA).

## Definition of Done

- [ ] PR mergeado em `main` com CI verde — todos os jobs novos da matrix
      `runtime` + `playwright` rodaram.
- [ ] [[ADR-248]] promovida `Proposto → Decidido (A20.L1)` com referência ao PR.
- [ ] `docker-compose.prod.yml` atualizado e operador notificado (mudança
      breaking de tag — staging recebe pull manual primeiro).
- [ ] `docker-compose.dev.yml` ([[A20.l6]]) referencia target `playwright` por
      default para que dev local mantenha PDF render funcionando.
- [ ] Runbook em `docs/reference/runbooks/docker_images.md` explica "quando
      trocar de target" e "como auditar enxutez do worker".
- [ ] Imagens publicadas no GHCR validadas com `docker pull
      ghcr.io/davidrobert/mathoms-backend:runtime-<sha>` e `docker run --rm
      <imagem> python --version` funcional fora do CI.
- [ ] Pre-flight smoke em staging: 3 PDFs de relatório sintético renderizam
      pelo service `api` (playwright); worker processa 1 task Celery sem
      stack-trace.
- [ ] [CHANGELOG](../../../CHANGELOG.md) entry registrada no merge.

## Riscos top 3

1. **Wheels nativos diferentes entre `builder` e `runtime`** (Python 3.12-slim
   bookworm muda glibc) — mitigação: builder usa exatamente o mesmo
   `python:3.12-slim` pinado por SHA ([[A20.l2]]/[[ADR-249]]) que o runtime.
   Validar `ldd` em wheels críticos (cryptography, asyncpg) durante smoke.
2. **Chromium libs faltando em runtime** — Playwright headless tem dependência
   silenciosa em algumas libs (`libatspi2.0-0` é o caso clássico que quebra só
   em PDF complexo). Mitigação: smoke test renderiza relatório completo com
   tabelas + gráficos + ícones, não só `<html>Hello</html>`.
3. **Cache GHA scope cross-target** — se BuildKit invalida cache do `runtime`
   no build do `playwright`, dobra o tempo de CI. Mitigação: `cache-to` com
   `mode=max,scope=${target}` força cache por target; medir cold vs warm em
   PR de prova.

## Métricas

- Tamanho imagem `runtime` (target <450MB, atual ~1.1GB → economia ~60%).
- Tamanho imagem `playwright` (target <950MB).
- Tempo de build `runtime` (cold + warm).
- Tempo de build `playwright` (cold + warm).
- Tempo de pull em staging (via `docker pull`) — proxy para custo de deploy.
- `docker exec worker ps -ef | wc -l` em `runtime` vs `playwright` (audita
  processos parasitas).

## Especialistas pre-PR

- **`sre-devops`** (obrigatório) — validar Dockerfile multi-stage, healthcheck,
  user não-root, layer ordering, ausência de secrets em ENV.
- **`build-vs-buy`** (consultivo) — confirmar que `playwright` como engine PDF
  segue [[ADR-076]] e não há janela de revisão de provedor de PDF agora.

## Pré-requisitos rígidos

- [[A20.l10]] mergeada (lockfile com hashes existe — `requirements.lock` +
  `backend/requirements.lock`).
- [[A20.l2]] **em paralelo**, não bloqueia início: SHA pin de `python:3.12-slim`
  vira `ARG PYTHON_BASE_SHA` neste Dockerfile, mas pode ser placeholder durante
  desenvolvimento. **Gate de merge:** L2 e L1 mergeiam no mesmo dia para
  garantir SHA pinado antes do release.

## Detalhe operacional

Track prompt em [`../tracks/a20-l1-backend-multistage.md`](../tracks/a20-l1-backend-multistage.md) (criado 2026-05-29; pós-F3/ADR-182 tracks vivem em `docs/sprint/<X>/tracks/`).
