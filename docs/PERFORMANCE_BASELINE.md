# PERFORMANCE_BASELINE — Footprint do `pipeline-service` Python

> **Status:** referência (não-plano) · **Data inicial:** 2026-04-27 · **Origem:** A2 do tópico "preparar contexto para Go rewrite" (proposto na conversa com CTO)
>
> **Escopo:** baseline empírico do `pipeline-service` Python para que o ADR de estratégia de port (Caminho 1/2/3 — ver [GO_PORT_DEPS.md](GO_PORT_DEPS.md)) seja escrito com dados, não com fé.
>
> **ADRs relacionadas:** [ADR-112](DECISIONS.md#adr-112--pipeline-as-service-http-boundary-para-execução-de-stages-a6f1) (HTTP boundary), [ADR-113](DECISIONS.md#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7) (convenções Go).

---

## TL;DR

| Métrica | Local (uvicorn) | Container (Docker) |
| --- | --- | --- |
| **Cold start** (até `/health` 200) | ~1.4s | ~440-1170ms (mediana ~500ms) |
| **Import time** (sem HTTP server) | 165ms | n/a |
| **RSS idle** (5s pós-boot) | 39 MB | 35.7 MB |
| **RSS pós-load** (5k req c=50) | 49 MB | 37.8 MB |
| **`/health` p50** (c=50) | 7ms | 14ms |
| **`/health` p99** (c=50) | 15ms | 174ms |
| **`/health` throughput** | ~7100 req/s | ~2700 req/s |

| Footprint | Valor |
| --- | --- |
| Imagem Docker (DISK USAGE arm64) | **283 MB** |
| Imagem Docker (CONTENT SIZE) | 60.7 MB |
| Site-packages (56 deps) | 43 MB |
| Top deps por tamanho | redis 4.2 MB · pydantic_core 4.3 MB · pydantic 4.0 MB · fastapi 1.4 MB · uvicorn 692 KB |

**Conclusão operacional:**

- O ganho potencial de Go está em (a) **image size** (283 MB → ~15-30 MB típico de binário Go estático) e (b) **cold start** (~500ms → <100ms típico). A diferença em `/health` throughput é informativa mas **não é o gargalo do produto** — stages reais levam minutos.
- Sem stage execution medida (ver §Limitações), não dá para concluir sobre footprint sob carga real do pipeline. **O baseline aqui cobre só o shell HTTP.**

---

## 1. Setup

**Ambiente:**

- macOS Darwin 25.3.0 · Apple Silicon (arm64)
- Python 3.12 (via Homebrew)
- Docker Desktop arm64 (linux/arm64 container)
- Redis local rodando (`redis-cli ping → PONG`) — não usado pelos benchmarks aqui (`/health` não toca Redis), mas presente
- Apache Bench (`ab`) como gerador de carga

**Versões instaladas no venv:**

```
fastapi 0.136.1
uvicorn (latest standard)
pydantic 2.13.3
pydantic_core 2.46.3
redis 7.4.0
httpx 0.28.1
websockets (latest)
```

(56 packages totais em [pipeline-service/pyproject.toml](../pipeline-service/pyproject.toml) deps + transitive)

**Setup local:**

```bash
python3.12 -m venv _scratch/.venv-ps
source _scratch/.venv-ps/bin/activate
pip install ./pipeline-service
cd pipeline-service && uvicorn app.main:app --host 127.0.0.1 --port 18001
```

**Setup container:**

> Nota: o [Dockerfile oficial do pipeline-service](../pipeline-service/Dockerfile) está com bug pré-existente — vide §6. Para esta medição usei um Dockerfile equivalente em `_scratch/` (gitignored) que apenas reordena `COPY` antes de `RUN pip install`. Wire-protocol e deps são idênticos.

```bash
docker build -t mathoms-pipeline-service:baseline -f _scratch/Dockerfile.pipeline-service-fixed .
docker run -d --name ps -p 18002:8001 mathoms-pipeline-service:baseline
```

---

## 2. Cold start

### Local (uvicorn direto)

| Métrica | Valor | Como medi |
| --- | --- | --- |
| `from app.main import app` (import puro) | **165 ms** | `time.monotonic()` antes/depois do import |
| `uvicorn` start → primeiro `/health` 200 | **1424 ms** | timestamp antes do `&` background, polling `curl` 50ms até 200 |

O import puro (165ms) é o **piso** do shell. O delta de ~1260ms até `/health` cobre uvicorn boot + binding + primeiro request handler. Comparativo: typical Go HTTP service com `chi` levanta em <50ms.

### Container (Docker arm64)

3 trials repetidos (`docker run -d → curl /health 200`):

| Trial | Tentativas até 200 | Cold start (ms) |
| --- | --- | --- |
| 1 | 8 | 496 |
| 2 | 7 | 437 |
| 3 | 14 | 1170 |

**Mediana ~500ms**, com cauda larga (1170ms na 3ª tentativa). Variação de 2.7× entre trials sugere overhead do Docker Desktop em macOS (VM Linux + bridge network) — não medido em Linux nativo.

### Por que o container é mais rápido que o local?

Hipóteses não validadas:

- Local: `source venv/bin/activate` + zsh prep + cold pip cache.
- Container: deps pré-instaladas no FS do container, scratch import sem caminhos de import customizados.

A diferença é **suspeita**, não conclusiva. Em Linux nativo prod, esperar valores mais próximos do local.

---

## 3. RSS (memória residente)

### Local

| Estado | RSS | VSZ |
| --- | --- | --- |
| Idle (5s pós-boot) | **39 MB** | 414 GB |
| Pós-load (5k req c=50) | **49 MB** | 415 GB |

Crescimento de ~10 MB sob carga é compatível com FastAPI/Pydantic alocando working set; estável depois.

### Container

| Estado | Mem usage | Max |
| --- | --- | --- |
| Idle | **35.7 MiB** | 7.75 GiB (cgroup default) |
| Pós-load (5k req c=50) | **37.8 MiB** | — |

Container é levemente mais leve que local — provavelmente porque dispensa overhead do shell parent e import paths customizados de `_ensure_pipeline_on_path()` em [main.py:24](../pipeline-service/app/main.py:24).

VSZ astronômico em macOS é normal (mmap virtual generoso); não corresponde a memória real comprometida.

---

## 4. Latência `/health`

### Local — `ab -n 1000 -c 10`

```
Requests per second:    6325 [#/sec]
Time per request:       1.581 ms (mean)
50%      1 ms
95%      2 ms
99%     13 ms
```

### Local — `ab -n 5000 -c 50`

```
Requests per second:    7085 [#/sec]
Time per request:       7.057 ms (mean)
50%      7 ms
95%     10 ms
99%     15 ms
100%    19 ms (longest)
```

### Container — `ab -n 5000 -c 50`

```
Requests per second:    2715 [#/sec]
Time per request:       18.4 ms (mean)
50%     14 ms
95%     31 ms
99%    174 ms
100%   223 ms
```

**Observação importante:** o container em macOS Docker Desktop tem p99 = 174ms vs. 15ms no local (diferença 11.6×). Quase certamente artefato da VM Linux + bridge network. Em prod arm64 Linux nativo, p99 deve ficar próximo do local.

### Para fins do ADR

`/health` é **proxy do overhead HTTP puro** — sem deserialização Pydantic, sem lógica de domínio, sem I/O. Útil para comparar ordens de grandeza:

- Python (FastAPI/uvicorn): p50 ~1-7ms · throughput ~7k req/s
- Go (chi/gin/stdlib): typical p50 ~0.1-0.5ms · throughput >50k req/s

Diferença é real (~10×), mas **fora do hot path do produto**. Stages reais levam minutos; `/health` overhead some no ruído.

---

## 5. Footprint de imagem e deps

### Imagem Docker

```
DISK USAGE: 283 MB    (descomprimido no node, inclui base layer python:3.12-slim)
CONTENT SIZE: 60.7 MB (camadas adicionadas pelo Dockerfile, transferred ao registry)
```

**Quebra das camadas adicionadas:**

| Camada | Tamanho |
| --- | --- |
| `pip install --upgrade pip` | 8 MB |
| `COPY pipeline-service` + `pipeline` | 16 KB + 5 MB |
| `pip install /repo/pipeline-service` (deps) | 44.6 MB |
| Outros (env, workdir, expose) | <1 MB |

A base `python:3.12-slim` adiciona ~120 MB. Para Go: `FROM scratch` ou `FROM gcr.io/distroless/static-debian12` é típico — base ~2-20 MB.

### Site-packages (43 MB total, 56 pkgs)

Top consumidores:

| Package | Tamanho | Necessidade |
| --- | --- | --- |
| `pydantic_core` | 4.3 MB | wire serialization (Caminho 3 Go: ~50 KB com `encoding/json`) |
| `redis` | 4.2 MB | pub/sub (Caminho 3 Go: `redis/go-redis` ~3-5 MB) |
| `pydantic` | 4.0 MB | DTOs (Caminho 3 Go: structs com tags, zero) |
| `fastapi` | 1.4 MB | router (Caminho 3 Go: chi ~500 KB) |
| `uvicorn` | 692 KB | ASGI server (Caminho 3 Go: net/http stdlib, zero) |

---

## 6. Achado colateral — bug pré-existente no Dockerfile

[pipeline-service/Dockerfile](../pipeline-service/Dockerfile) **não builda como está hoje** (testado em 2026-04-27, arm64).

Causa: linha 14 copia só `pyproject.toml` antes do `pip install` na linha 15. Mas `pyproject.toml` declara `[tool.setuptools] packages = ["app", "app.api", ...]` — setuptools tenta encontrar o diretório `app/` durante o build do wheel e falha:

```
error: package directory 'app' does not exist
ERROR: Failed to build 'file:///repo/pipeline-service'
```

**Workaround usado:** `_scratch/Dockerfile.pipeline-service-fixed` reordena para copiar `pipeline-service/` e `pipeline/` **antes** do `pip install`. Não é o layout caching-friendly do original (pyproject deveria ir antes para cachear deps), mas funciona.

**Fix correto** (proposta para slice próprio, fora desta task):

```dockerfile
# Copia pyproject + app primeiro para que setuptools encontre os pacotes,
# mas mantém deps cacheadas separando install em duas etapas (deps via
# constraints/requirements.txt, depois código + install editable).
COPY pipeline-service/pyproject.toml /repo/pipeline-service/
COPY pipeline-service/app /repo/pipeline-service/app
RUN pip install --upgrade pip && pip install /repo/pipeline-service
COPY pipeline /repo/pipeline
```

**Implicação para A3:** se o ADR de port for Caminho 1 (shell-only Go), o Dockerfile Python precisa ser fixado **antes** — caso contrário não dá para validar paridade de comportamento entre Python e Go via container.

---

## 7. Limitações desta medição

### O que **NÃO** foi medido

1. **Stage execution real (`POST /api/v1/pipeline/stages/{name}/execute`)** — exige `workspace_root` com dados financeiros reais (extratos, faturas, baseline). Out-of-scope sem orquestração combinada com smoke tenant. **Esse é o número que mais importa para o ADR de port** — sem ele, não dá para afirmar quanto tempo um stage E3/E5 leva sob Python vs. Go.
2. **Concorrência alta sustentada** — `ab -n 5000 -c 50` é micro-benchmark. Carga real de produção (rajadas, idle longos) não testada.
3. **WebSocket `/api/v1/pipeline/events/{run_id}`** — não medido. Throughput de Redis pub/sub não foi exercitado.
4. **Linux nativo** — todas as medidas são macOS (local) ou macOS Docker Desktop (container, VM Linux + bridge). Prod Linux nativo arm64/amd64 deve ter números melhores em latência/cold start.
5. **Memory growth sob carga prolongada** — RSS estabilizou em ~49 MB (local) / 37.8 MB (container) após 5k requests, mas não há teste de leak em horas de carga.
6. **Comparação direta com Go** — não foi implementada. Os números "típicos Go" no doc são baseados em benchmarks públicos de chi/gin/stdlib + `oapi-codegen`, não medições nesta máquina.

### Honestidade sobre números

- Latências p99 do container (174ms) parecem ruído de Docker Desktop em macOS, não comportamento real de prod.
- Throughput `/health` ~7k req/s (local) é razoável para FastAPI single-worker; production usaria `--workers N` (Gunicorn/uvicorn) e ficaria proporcional a `N` até saturar I/O.
- Cold start mediana ~500ms no container é dominado por Python interpretador + import time (165ms baseline) + uvicorn boot. Não há reserva mágica a ser otimizada em Python.

---

## 8. O que isso significa para o ADR de port

Refinando a análise de [GO_PORT_DEPS.md §3](GO_PORT_DEPS.md#3-caminho-de-port--análise-quantitativa) com dados:

### Caminho 1 — Shell-only Go + Python via subprocess

- **Ganha:** image 283 MB → ~30 MB (Go estático + Python embedded ou base distroless). Cold start <100ms.
- **Não muda:** RSS sob carga real do pipeline (Python continua executando os stages). `/health` overhead idem (Python era proxy; Go é proxy melhor mas é proxy).
- **Adiciona:** custo de `fork+exec` Python por stage (~50-200ms cold). Stages levam minutos → diluído.

### Caminho 2 — Roteador Go + Python worker pool

- Mesmos ganhos do Caminho 1.
- Elimina `fork+exec` por request — mantém Python warm.
- **Custo:** complexidade operacional (worker pool lifecycle, restart policy).

### Caminho 3 — Reescrita completa em Go

- **Ganha tudo:** image ~10-20 MB · RSS pleno · cold start <50ms · sem GIL.
- **Custo:** port de 13.077 LOC de domain services com paridade obrigatória contra goldens BRL (`0.01` tolerance). 3-5 meses dedicados, conforme [GO_PORT_DEPS.md](GO_PORT_DEPS.md).

### Decisão honesta para A3

Se o **gatilho** da migração for "footprint de container e cold start" → Caminho 1 entrega 90% do ganho com 5% do custo.

Se o gatilho for "throughput sob alta concorrência" ou "GIL no hot path" → Caminho 3 é o único que entrega; **mas a evidência empírica para esse gatilho ainda não existe** (stage execution real não medida nesta task).

A2 sugere fortemente que **Caminho 1 é o trade-off pragmático default**, a menos que A3 receba evidência adicional de gargalo CPU-bound nos stages. Esse dado precisa de A2.1 (extensão): rodar um workspace smoke real e medir RSS/CPU por stage executado.

---

## 9. Reproduzir este baseline

```bash
# 1. Setup venv e deps
python3.12 -m venv _scratch/.venv-ps
source _scratch/.venv-ps/bin/activate
pip install ./pipeline-service psutil httpx

# 2. Import time (puro)
cd pipeline-service && python -c "
import time
t0 = time.monotonic()
from app.main import app
print(f'import_ms={1000*(time.monotonic()-t0):.1f}')
"

# 3. Cold start local
(uvicorn app.main:app --host 127.0.0.1 --port 18001 &)
T0=$(python3 -c "import time; print(time.monotonic())")
for i in $(seq 1 200); do
  if curl -sf http://127.0.0.1:18001/health > /dev/null 2>&1; then
    T1=$(python3 -c "import time; print(time.monotonic())")
    python3 -c "print(f'ready_ms={1000*($T1-$T0):.0f}')"
    break
  fi
  sleep 0.05
done

# 4. RSS idle
PID=$(lsof -ti:18001)
sleep 5
ps -o rss=,vsz=,pcpu= -p "$PID"

# 5. Latência
ab -n 5000 -c 50 -q http://127.0.0.1:18001/health

# 6. Container (após fix do Dockerfile — ver §6)
docker build -t mathoms-pipeline-service:baseline -f _scratch/Dockerfile.pipeline-service-fixed .
docker images mathoms-pipeline-service:baseline
docker run -d --name ps -p 18002:8001 mathoms-pipeline-service:baseline
docker stats ps --no-stream --format "{{.MemUsage}}"
ab -n 5000 -c 50 -q http://127.0.0.1:18002/health
docker stop ps && docker rm ps
```

Atualizar este doc se: (a) shell ganhar dependência nova relevante (Pydantic, FastAPI version bump); (b) Dockerfile for fixado; (c) novos endpoints forem adicionados ao shell.

---

## 10. Próximos passos sugeridos

| # | Ação | Por quê |
| - | --- | --- |
| **A1** | Inventário de deps · [GO_PORT_DEPS.md](GO_PORT_DEPS.md) | ✅ feito |
| **A2** | Este documento · footprint baseline | ✅ feito (com limitação: stage execution real não medida) |
| A2.1 | Estender A2 com smoke real — workspace tenant + um run E0→E5, medir RSS/CPU/duração por stage | Sem isso, gatilho "GIL" para Caminho 3 fica especulativo |
| **A3** | ADR de estratégia de port (Caminho 1/2/3) com base em A1 + A2 (+ A2.1 se necessário) | Destrava primeiro PR Go produtivo |
| A2.fix | Slice próprio para fixar [pipeline-service/Dockerfile](../pipeline-service/Dockerfile) — pré-requisito para CI smoke do pipeline-service Python | Detectado em A2 §6 |
