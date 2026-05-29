---
id: A20.l1
type: lane
title: "Docker dev↔prod parity — L1 Multi-stage backend + Playwright dual target"
sprint: A20
status: shipped
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
  - status/shipped
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

## Status de entrega (2026-05-29)

✅ **Entregue.** Fonte de verdade é o [`Dockerfile`](../../../../Dockerfile) real
(3 stages, dual target). Esta lane preserva o racional; o snippet abaixo é
pointer + as **duas correções** que emergiram na implementação vs o draft.

### Correção 1 — lockfile único, não dois

O draft assumia `requirements.lock` **+** `backend/requirements.lock` (dois
arquivos copiados/instalados). [[A20.l10]] entregou **um único** `requirements.lock`
na raiz (`pip-compile` sobre `requirements.in` + `backend/requirements.in` —
o lock da raiz já é o superset). O Dockerfile copia/instala só ele.

### Correção 2 — wheels via bind-mount, não `COPY --from=builder /wheels`

O draft fazia `COPY --from=builder /wheels` + `rm -rf /wheels`. **Isso deixa
~157MB mortos na imagem:** um `RUN rm` posterior não reclama a layer do `COPY`
anterior. Medido empiricamente — runtime ficou em **1.4GB**. Fix: BuildKit
bind-mount transitório, que nunca vira layer persistente:

```dockerfile
COPY requirements.lock /app/requirements.lock
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    pip install --require-hashes --no-index --find-links /wheels -r /app/requirements.lock
```

Runtime caiu para ~1.09GB. Requer `# syntax=docker/dockerfile:1.7` (já no topo).

### Correção 3 — SHA pin fica em L2, não placeholder em L1

O draft tinha `ARG PYTHON_BASE_SHA=sha256:TBD_PIN_L2` com `@${PYTHON_BASE_SHA}`.
L1 entrega `ARG PYTHON_BASE=python:3.12-slim` (tag) — [[A20.l2]] troca o default
por `python:3.12-slim@sha256:<digest>` num **único ponto** sem reescrever os 3
`FROM`. Evita Dockerfile que não builda até L2 mergear.

O restante (3 stages `builder→runtime→playwright`, `FROM runtime AS playwright`,
build-essential só no builder, libs Chromium enxugadas, non-root UID 1000,
healthcheck curl, `python -m playwright install chromium`) saiu como desenhado.

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

> **Tamanho absoluto saiu dos critérios.** As metas <450MB / <950MB do draft
> são fisicamente impossíveis (runtime real ~1.09GB, playwright ~2.72GB arm64 —
> ~652MB de site-packages irredutível; ver [[ADR-248]] §Validação). O deliverable
> são os **dois invariantes do dual-target**, fixados por
> [`dev/audit_backend_image.sh`](../../../../dev/audit_backend_image.sh):

1. ✅ **runtime sem `gcc`** — `docker run --rm --entrypoint sh runtime-test -c
   'command -v gcc'` falha (build-essential vive só no `builder` descartado).
2. ✅ **runtime sem cache `ms-playwright`** — `/home/mathoms/.cache/ms-playwright`
   ausente no runtime (worker/beat não carregam ~956MB de Chromium).
3. ✅ `docker run --rm --entrypoint python playwright-test -m playwright --version`
   imprime versão sem stack trace.
4. ✅ Cache `ms-playwright` **presente** no target `playwright` (PDF render
   não quebrado — P0.1).
5. ✅ Heredity: `docker history playwright-test --format '{{.CreatedBy}}' |
   grep 'playwright install'` (prova `FROM runtime AS playwright`).
6. ✅ Build sem `--target` (default) produz imagem `playwright`.
7. ✅ `requirements.lock` (único, raiz) consumido via `--require-hashes
   --no-index` ([[A20.l10]] / [[ADR-254]]).
8. ✅ `docker-compose.dev.yml` ([[A20.l6]]) usa target `playwright` no `api` e
   `runtime` no worker/beat; `docker compose config --quiet` valida.

**Deferido para [[A20.l4]]** (release-backend.yml, fora do escopo de L1):
smoke render PDF end-to-end, audit worker via `ps -ef` em prod, `hadolint`
verde (após SHA pin de L2), CI matrix ≤6min.

## Definition of Done

- [x] PR mergeado em `main` com CI verde (Dockerfile + audit + dual-target dev compose).
- [x] [[ADR-248]] promovida `Proposto → Decidido (A20.L1)` com critérios de
      tamanho revisados para a realidade empírica.
- [x] `docker-compose.dev.yml` ([[A20.l6]]) usa target `playwright` no `api`
      (PDF render) e `runtime` no worker/beat.
- [x] `dev/audit_backend_image.sh` fixa os dois invariantes do dual-target.
- [x] Runbook em [`docs/reference/runbooks/docker_images.md`](../../../reference/runbooks/docker_images.md).
- [x] CHANGELOG entry registrada.

**Deferido para [[A20.l4]]** (release-backend.yml + GHCR + Coolify):
`docker-compose.prod.yml` por target, publicação no GHCR, pre-flight smoke
em staging com 3 PDFs sintéticos. `docker-compose.prod.yml` **não** foi tocado
em L1 (decisão sre-devops — evita mudança breaking de tag sem o pipeline de
release pronto).

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

## Métricas (empíricas, arm64 · Docker 29.4)

- Tamanho `runtime` ~1.09GB (~652MB site-packages irredutível). Ganho real:
  build-essential fora + sem Chromium, não número absoluto.
- Tamanho `playwright` ~2.72GB (runtime + ~956MB Chromium + ~228MB libs).
- **Economia de ~956MB de Chromium em 2 dos 3 containers** (worker + beat) —
  esse é o win de FinOps/RAM que o dual-target entrega.
- Tempo de build (warm, bind-mount wheels): runtime ~13s, playwright +Chromium.
- `chromium-headless-shell` (~110MB vs ~956MB full) é alavanca de slimming
  futura — [[TRACK-a20-fu-chromium-headless-shell]], não L1 (muda comportamento
  de render; exige gate de paridade visual do PDF).

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
