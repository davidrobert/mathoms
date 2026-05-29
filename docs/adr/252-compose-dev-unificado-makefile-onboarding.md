---
id: ADR-252
type: adr
title: "Compose dev unificado + Makefile targets opt-in — Sprint A20"
status: Proposto
phase: A20.l6
date: "2026-05-22"
relates_to:
  - "[[ADR-248]]"
  - "[[ADR-250]]"
  - "[[ADR-253]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 252"
  - "Docker compose dev"
  - "Makefile onboarding"
tags:
  - type/adr
  - status/proposto
  - area/infra
  - area/devops
  - area/dx
  - phase/a20
---

## Contexto

Review independente `sre-devops` (2026-05-22) identificou **P1.6**: dev
local não usa Docker. Backend roda `uvicorn` no host (Python local +
Postgres local + Redis local), frontend roda `npm run dev`. **Paridade
dev↔prod fraca** — bugs específicos de glibc/libc6/Debian slim só aparecem
em staging.

KPI norte-mágico do sprint A20: **TTFR (Time-To-First-Request)** para novo
dev. Baseline ~25min (instalar Python + Postgres + Redis + Alembic + seed).
Alvo: <5min (`make dev-up-docker && curl localhost:8000/health`).

Gap adicional identificado pelo `senior-cto` review: **5 compose files** já
existem (`docker-compose.yml`, `dev.yml`, `prod.yml`, `smoke.yml`,
`test.yml`). Criar 6º ("compose dev unificado") sem matar legados é
proliferação.

A decisão precisa endereçar: (a) compose dev viável com hot-reload e seed
automático; (b) cleanup de composes legados; (c) Makefile targets opt-in
(não substituir uvicorn local); (d) políticas de healthcheck por service
(complementa [[A20.l3]]).

## Decisão

### D1 — `docker-compose.dev.yml` unificado

Cria `docker-compose.dev.yml` orquestrando stack completa para dev local:

- 7 services: `postgres`, `redis-broker`, `redis-cache`, `api`, `worker`,
  `beat`, `frontend`.
- Volumes para hot-reload: `./backend:/app/backend:ro,delegated` (macOS) +
  `./frontend:/app/frontend:cached` + `./config:/app/config:ro`.
- `uvicorn --reload --reload-dir backend/app` em api command (não watch tudo).
- Seed automático: `entrypoint.dev.sh` roda `alembic upgrade head` +
  `dev/seed_minimal_workspace.py` se DB vazio (idempotente).
- Override `docker-compose.dev.override.yml.example` documenta vars locais.
- Imagem base referenciada com tag `playwright-latest` (default — superset
  seguro pra dev rodar tudo, incluindo PDF render).

### D2 — Cleanup de composes legados

Estado final pós-A20 (4 compose files):

| Arquivo | Decisão | Motivo |
|---|---|---|
| `docker-compose.yml` (Redis-only) | **DELETAR** | Redundante com novo `dev.yml` |
| `docker-compose.dev.yml` (frontend-ops antigo) | **REESCRITO** | Novo dev unificado |
| `docker-compose.prod.yml` | **MANTER** | Source-of-truth prod |
| `docker-compose.smoke.yml` | **MANTER** | CI smoke |
| `docker-compose.test.yml` | **MANTER** | E2E local |
| `pipeline-service/docker-compose.yml` | **MANTER** | Service-específico |

### D3 — Makefile targets opt-in

Targets novos no `Makefile` (entregue em [[A20.l7]] · todos com sufixo
**`-docker`** para não colidir com a stack uvicorn-local legada
`dev-up`/`dev-down`/`dev-logs`, que já existem):

- `make dev-up-docker` — sobe stack completa (`up -d --build` + guard de porta)
- `make dev-down-docker` — para tudo, preserva volumes
- `make dev-reset-docker` — para + apaga volumes (`down -v`)
- `make dev-shell-docker` — shell drop no container `api`
- `make dev-rebuild-docker` — rebuild após mudança em deps
- `make dev-logs-docker` — `logs -f` (`SVC=<nome>` filtra um service)

`uvicorn` local continua suportado via `make dev-up` legado (sem `-docker`).

### D4 — Healthcheck por service em compose

Move `HEALTHCHECK` do `Dockerfile` backend (multi-modo bug) para
`docker-compose.prod.yml` e `dev.yml` por service:

- `api`: `curl --fail http://localhost:8000/health`
- `worker`: `celery -A backend.app.worker inspect ping`
- `beat`: `find /tmp/celerybeat.pid -mmin -2` (PID file freshness)
- `pipeline-service`: `curl --fail http://localhost:8001/health`

Política comum: `interval: 30s`, `timeout: 5s`, `start_period: 30s`,
`retries: 3`.

### D5 — `SETUP.md` revisado

Docker vira **caminho recomendado** com seção "Onboarding em <5min" no topo;
uvicorn local mantido como fallback documentado.

## Alternativas consideradas

### Opção A — Substituir totalmente uvicorn local

**Rejeitada.** Quebra DX de quem prefere debugger nativo. Migração ativa
exige comunicação + risco de regressão. Mantém uvicorn como opt-out.

### Opção B — Híbrido fixo (DB/Redis em Docker, app no host)

**Rejeitada.** Já é 80% do `smoke.yml`. Ganho marginal sobre status quo.
Não resolve P1.6 (paridade dev↔prod).

### Opção C — Compose dev + Makefile (adotada)

Resolve TTFR, paridade, e opt-in. Mantém uvicorn legado. Custo: duas
estratégias para suportar durante A20.

## Consequências

### Positivas

- **TTFR cai de ~25min para <5min** (KPI principal A20).
- **Paridade dev↔prod** — mesmas imagens, mesmas libs, mesma config.
- **Healthchecks corretos** por service.
- **5 → 4 compose files** (cleanup).

### Negativas

- **Suporte de 2 caminhos** durante A20 (Docker + uvicorn) — custo de manter
  ambos. Deprecação de uvicorn fica como FU pós-dogfood.
- **Bind mount em macOS** — `delegated` ajuda mas não elimina latência.

### Neutras

- **Custo de imagem dev** — usa `playwright-latest` (superset). Imagem mais
  pesada que `runtime` mas dev tem espaço.

## Validação

Critérios em [[A20.l3]] (healthchecks), [[A20.l6]] (compose dev), [[A20.l7]]
(Makefile).

### Notas de entrega — L6 (D1+D2, 2026-05-29)

D1+D2 implementados e validados empiricamente contra `postgres:16-alpine`
(`up -d --build` → `/health` 200, `database/redis/redis_cache: ok`, seed =
1 workspace, hot-reload do bind mount confirmado). Desvios conscientes do
desenho original (sre-devops review), a refletir em L3/L7:

- **Mounts sem `:delegated`/`:cached`** — no-op em VirtioFS (Docker Desktop
  moderno). `pgdata`/`redisdata`/`storage` em named volumes (UID 1000 não
  escreve em dir do host macOS via bind).
- **`entrypoint` override, não `command`** — o Dockerfile usa
  `ENTRYPOINT`+`CMD` (dispatch `api|worker|beat`); sobrescrever `command`
  cairia no dispatch errado. Invocado via `bash /app/dev/entrypoint.dev.sh`
  (independe do x-bit do bind mount). `dev/` chega por bind mount (Dockerfile
  não copia `dev/`).
- **Imagem `mathoms-backend:dev`** buildada do `Dockerfile` atual — o alvo
  `playwright-latest` (superset PDF) chega em [[A20.l1]] (multi-stage).
- **`worker`/`beat` healthcheck `disable: true`** (paridade prod) — o
  `inspect ping` por service é entregue em [[A20.l3]] (este ADR D4).
- **Bug latente de paridade corrigido** — migration `adr223` emitia
  `SET DEFAULT 0` em coluna BOOLEAN (Postgres `DatatypeMismatchError`); só
  SQLite tolerava. Exposto pelo boot Docker contra Postgres real; fix em PR
  separado (default por dialeto).

Status permanece **Proposto** até L3 (D4) e L7 (D3/D5) entrarem; flip para
`Decidido` no merge da última lane do ADR.

## Migração

Fases em §Lanes: L3 (XS, Onda A), L6 (M, Onda A), L7 (S, Onda B).

## Riscos

- **Performance bind mount macOS** — `delegated` + fallback rebuild rápido.
- **Seed automático falha em re-run** — idempotência via `ON CONFLICT DO
  NOTHING`.
- **`uvicorn --reload` consome CPU em watch grande** — `--reload-dir`
  específico.

## Métricas

- TTFR (target <5min, baseline ~25min).
- Hot-reload latency (target <3s).
- Composes em repo (target = 4, baseline = 5).
- Adesão Docker em dev local (target >50% após 1 sprint dogfood).

## Referências externas

- [Docker compose dev best practices](https://docs.docker.com/compose/development/)
- [uvicorn `--reload` config](https://www.uvicorn.org/settings/#development)
