# Runbook — Healthchecks por service (Docker)

> **ADR:** [[ADR-252]] (D4 · A20.L3) · **Lane:** [[A20.l3]]
> **Compose:** [`docker-compose.prod.yml`](../../../docker-compose.prod.yml) · [`docker-compose.dev.yml`](../../../docker-compose.dev.yml)
> **Owner:** quem tocar healthcheck de service, `Dockerfile` backend ou `pipeline-service/Dockerfile`.

---

## 1. Onde cada healthcheck vive (e por quê)

A imagem **backend é multi-modo** (`api`/`worker`/`beat` via um único
entrypoint). Um `HEALTHCHECK` no Dockerfile aplicaria o mesmo comando aos três
modos — mas só o `api` expõe HTTP. Por isso o healthcheck **não vive no
Dockerfile backend**; cada service declara o seu no compose.

A imagem **pipeline-service é single-modo** (sempre `uvicorn :8001`) — aí o
`HEALTHCHECK` vive **no próprio Dockerfile** (paridade com k8s/ECS, que leem a
instrução da imagem).

| Service | Healthcheck | Onde declarado |
|---|---|---|
| `api` | `curl -fsS localhost:8000/health` | compose (start_period 60s — alembic) |
| `worker` | `celery -A backend.app.worker inspect ping` | compose |
| `beat` | **nenhum** (ver §3) | — |
| `pipeline-service` | `python -c "urllib...:8001/health"` | `pipeline-service/Dockerfile` |
| `postgres` / `redis-*` / `frontend` | nativo da imagem base | compose |

> O módulo Celery é `backend.app.worker` (variável `celery_app`, app `"fin"`).
> **Não** é `backend.celery_app` — esse path não existe.

---

## 2. worker — `inspect ping`

`worker` não expõe HTTP. Liveness via Celery control: `inspect ping` faz um
round-trip pelo broker e responde `pong` se há worker vivo. Em Celery 5.2+
(repo usa 5.6.3) o comando retorna **exit non-zero** quando nenhum worker
responde — base segura para o check.

```yaml
healthcheck:
  test: ["CMD-SHELL", "celery -A backend.app.worker inspect ping || exit 1"]
  interval: 30s
  timeout: 15s        # reply passa pela fila; sob carga atrasa
  start_period: 45s   # worker carrega app + conecta no broker no boot
  retries: 3
```

Broadcast (sem `-d`): em fleet de 1, targeted e broadcast são equivalentes;
`-d celery@$HOSTNAME` adiciona dependência frágil do nodename. Revisitar
cache/targeting quando worker = N+1.

---

## 3. beat — por que NÃO tem healthcheck

`beat` roda como **PID 1** (`exec celery ... beat`). Se crashar, o container
morre → `restart: unless-stopped` reinicia. Não há liveness barato e honesto:

- `inspect ping` é só para **workers** — beat não responde.
- pidfile (`--pidfile` + `test -f`) prova "um dia escreveu o arquivo", não
  liveness. PID 1 morto com pidfile stale → check passa **verde** mascarando a
  morte. Pior: `celery beat` recusa subir se um pidfile stale existir, criando
  crash-loop falso.
- freshness do `celerybeat-schedule` (shelve) depende de formato interno sem
  contrato.

Decisão (sre-devops · A20.L3): **beat sem healthcheck**, liveness via restart
policy, com comentário inline no compose explicando.

---

## 4. pipeline-service — non-root + urllib

`pipeline-service` rodava como **root** (P0.4). Agora: `useradd -u 1000
mathoms` (mesmo UID do backend) + `USER mathoms`. O healthcheck usa `urllib`
em vez de `curl` (base `python:3.12-slim` não traz curl; menos superfície):

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=5)" || exit 1
```

`timeout=5` no `urlopen` impede o check de pendurar.

---

## 5. Debugar healthcheck flaky

```bash
# Estado + últimas saídas do probe
docker inspect <container> --format '{{json .State.Health}}' | python3 -m json.tool

# Rodar o comando do worker manualmente
docker compose exec worker celery -A backend.app.worker inspect ping

# Ver os 4 services de saúde de uma vez
docker compose ps --format json | python3 -c "import sys,json;[print(j['Service'],j.get('Health')) for j in map(json.loads,sys.stdin)]"
```

| Sintoma | Causa provável | Ação |
|---|---|---|
| `api` unhealthy nos primeiros 60s | alembic ainda migrando | esperar `start_period`; ver `logs api` |
| `worker` unhealthy mas processa tasks | `start_period` curto / broker lento subindo | confirmar Redis healthy primeiro; subir `start_period` |
| `worker` `inspect ping` trava | broker inacessível | checar `redis-broker` healthy + DSN |
| `beat` reiniciando em loop | crash real do scheduler | `logs beat` — não é healthcheck (beat não tem) |
| `pipeline-service` unhealthy | `/health` não responde / porta errada | `docker exec ... python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8001/health').read())"` |

---

## 6. Checklist ao adicionar service novo

- HTTP exposto e single-modo → `HEALTHCHECK` no Dockerfile (urllib se sem curl).
- Multi-modo ou sem HTTP → healthcheck por service no compose.
- Sempre par com `restart: unless-stopped` — sem ela, Compose só **reporta**
  unhealthy, não reinicia.
- `start_period` cobre o boot real (migração, conexão a broker/DB).
