# Runbook: Dev environment em Docker (`docker-compose.dev.yml`)

**ADR:** [[ADR-252]] (D1+D2) · **Sprint:** A20.L6
**Compose:** `docker-compose.dev.yml`
**Substitui:** subida manual de Postgres/Redis local da seção legada de [SETUP](../SETUP.md).

Stack completa de dev local em Docker, com paridade dev↔prod (mesma
topologia de `docker-compose.prod.yml`) + hot-reload e seed automático.
Resolve P1.6 (dev local não usava Docker) e ataca o KPI de TTFR do A20
(baseline ~25min → alvo <5min).

---

## 1. Subir a stack

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Sobe 7 services: `postgres`, `redis-broker`, `redis-cache`, `api`,
`worker`, `beat`, `frontend`. O container `api` roda
`bash /app/dev/entrypoint.dev.sh` no boot:

1. `alembic -c backend/alembic.ini upgrade head`
2. `python /app/dev/seed_minimal_workspace.py` (idempotente — short-circuit
   se já existe workspace)
3. `uvicorn backend.app.main:app --reload --reload-dir backend/app`

Healthcheck do `api` tem `start_period: 60s` (cold build + migração + seed).

| Serviço | Host | Notas |
|---|---|---|
| API | http://localhost:8000 | `/health` → 200 quando pronto |
| Frontend | http://localhost:3000 | Next.js dev (HMR via `npm run dev`) |
| Postgres | `127.0.0.1:5432` | user/db `mathoms`, senha `devpass` (dev-only) |
| Redis broker | interno `6379` | `noeviction` (paridade prod) |
| Redis cache | interno `6379` | `allkeys-lru` |

Console interno (`frontend-ops`, ADR-116) é opcional:

```bash
docker compose -f docker-compose.dev.yml --profile ops up -d
```

---

## 2. Verificação (smoke)

```bash
# API saudável
curl -fsS http://localhost:8000/health        # → {"api":"ok", "database":"ok", ...}

# DB seedado
docker compose -f docker-compose.dev.yml exec postgres \
  psql -U mathoms -d mathoms -tAc 'select count(*) from workspaces'   # → >= 1

# Alembic na head
docker compose -f docker-compose.dev.yml exec postgres \
  psql -U mathoms -d mathoms -tAc 'select version_num from alembic_version'
```

Hot-reload: editar arquivo em `backend/app/**` → uvicorn recarrega em <3s
(visível em `docker compose -f docker-compose.dev.yml logs -f api`). O
watcher é restrito a `backend/app` (`--reload-dir`) — watchar `/app`
inteiro satura CPU em macOS.

---

## 3. Operação diária

Atalhos `make` (A20.L7 · sufixo `-docker` distingue da stack uvicorn-local
legada `make dev-up`/`dev-down`):

```bash
make dev-up-docker        # sobe a stack (build + migrate + seed)
make dev-logs-docker      # logs -f (SVC=api para um só service)
make dev-shell-docker     # bash no container api
make dev-down-docker      # para, PRESERVA volumes
make dev-reset-docker     # DESTRUTIVO: down -v (wipe DB/Redis/storage)
make dev-rebuild-docker   # rebuild imagens após mudar deps/Dockerfile
```

Equivalentes diretos em `docker compose` (sem o atalho):

```bash
docker compose -f docker-compose.dev.yml logs -f api     # logs
docker compose -f docker-compose.dev.yml down            # para (mantém dados)
docker compose -f docker-compose.dev.yml down -v         # wipe DB/Redis/storage
docker compose -f docker-compose.dev.yml exec api bash   # shell no api
```

---

## 4. Vars locais (override)

O Compose só carrega `docker-compose.override.yml` automaticamente quando o
arquivo base é `docker-compose.yml`. Como aqui usamos `-f
docker-compose.dev.yml`, passe os dois explicitamente:

```bash
cp docker-compose.dev.override.yml.example docker-compose.dev.override.yml
# edite (gitignored), então:
docker compose -f docker-compose.dev.yml -f docker-compose.dev.override.yml up -d
```

Casos comuns: `ANTHROPIC_API_KEY` real para exercitar LLM (E0/E2/E5/E6),
secret/Fernet próprios (`dev/gen-secrets.sh`), ou apontar `frontend-ops`
para um `api` no host.

> ⚠️ As senhas default (`:-devpass`) e as chaves `MATHOMS_SECRET_KEY` /
> `MATHOMS_FERNET_KEY` no compose são **dev-only**. **NUNCA aponte este
> compose para um DB real.**

---

## 5. Troubleshooting

| Sintoma | Causa provável | Ação |
|---|---|---|
| `api` reinicia em loop | migração ou seed falhando | `docker compose -f docker-compose.dev.yml logs api` |
| `bind: address already in use :8000` | `make dev-up` (uvicorn host legado) já roda na 8000 | pare o uvicorn local (`make dev-down`) **ou** mude a porta publicada via override |
| `/app/dev/entrypoint.dev.sh: No such file` | `dev/` não montado | confirme o bind mount `./dev:/app/dev:ro` no compose |
| Seed não cria workspace | DB já tinha workspace (idempotência) | esperado — `down -v` para resetar |
| Migração aborta em `DatatypeMismatchError` | default de tipo incompatível no Postgres | bug de paridade dev↔prod — corrigir a migration (literal por dialeto) |

---

## 6. Decisões de design (sre-devops · A20.L6)

- **Bind mounts read-only SEM `:delegated`/`:cached`** — no-op em VirtioFS
  (Docker Desktop moderno). `pgdata`/`redisdata`/`storage` ficam em named
  volumes (UID 1000 não escreve em dir do host macOS via bind).
- **`entrypoint` override (não `command`)** — o Dockerfile usa
  `ENTRYPOINT`+`CMD` (dispatch `api|worker|beat`); sobrescrever `command`
  cairia no dispatch errado. Invocado via `bash` para não depender do x-bit
  do bind mount.
- **Redis broker `noeviction` + cache `allkeys-lru`** idênticos a prod — a
  paridade existe para pegar o bug de eviction de mensagem Celery.
- **`worker`/`beat` healthcheck `disable: true`** (paridade prod). O
  healthcheck Celery `inspect ping` por service é entregue em [[A20.l3]].
