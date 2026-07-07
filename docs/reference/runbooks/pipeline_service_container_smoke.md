# Runbook — Smoke do pipeline-service em container (gate ADR-303)

> **ADR:** [[ADR-303]] (§Escopo deferido — enablement do container, fechado) · **Plano:** [[PLAN-go-shell]]
> **Dockerfile:** [`pipeline-service/Dockerfile`](../../../pipeline-service/Dockerfile) · **Overlay:** [`docker-compose.pipeline-service.yml`](../../../docker-compose.pipeline-service.yml)
> **Gate:** [`dev/smoke_pipeline_service_container.py`](../../../dev/smoke_pipeline_service_container.py)
> **Owner:** quem tocar o Dockerfile do pipeline-service, o overlay ou o boundary de artefatos (ADR-212/303).

---

## 1. O modelo mental em uma frase

A imagem do pipeline-service carrega `backend/` + deps do `requirements.lock`
(pós-ADR-303, executar stage exige `DBArtifactStore` + hidratação via
`run_context_factory`), e o gate prova **stage real via HTTP persistindo em
`pipeline_artifacts`** — o caminho que quebrou em silêncio antes do #723
não pode regredir mudo nem no Docker.

## 2. Procedimento

```bash
make smoke-up                    # Redis + DB migrado + fernet key (pré-requisito)
make smoke-pipeline-service     # builda a imagem, sobe o container e roda o gate
# ... saída esperada: "GATE ADR-303 (container): PASSA"
make smoke-pipeline-service-down # derruba só o container
make smoke-down                  # (opcional) derruba o stack inteiro
```

O gate: cria workspace em `_smoke_storage/ps-smoke-<ts>/` (bind-mounted),
seeda um E2 sintético **via `docker exec`**, POSTa
`stages/reconcile_transactions/execute` (timeout 180s) e lê o E3 de volta
**via `docker exec`** — falha alto em qualquer elo.

## 3. Restrições que você precisa saber antes de "melhorar" isto

- **SQLite WAL não é coerente entre host e container.** O smoke DB roda
  `journal_mode=WAL`; o `-shm` é mmap compartilhado que o virtioFS não
  propaga — escrita de um lado fica invisível do outro até checkpoint. Por
  isso o gate faz seed/readback **dentro do container** (um namespace só).
  Não converta para sessão do host "para simplificar": foi tentado, o
  container não via o seed e o host não via o E3. Acesso simultâneo
  host↔container ao mesmo arquivo é **não-suportado**; paridade prod-like
  com dois processos exige Postgres (F2 do plano GO_SHELL).
- **Smoke é sequencial por contrato** (seed → execute → readback). Sem
  concorrência de escritores.
- **Mounts do overlay ⇄ COPYs do Dockerfile devem ficar em sync**
  (`pipeline`, `pipeline-service`, `backend`, `scripts`, `config`) — mount
  ausente = container roda cópia stale do build e o "fix que não muda nada".
- **`MATHOMS_FERNET_KEY` = a key do smoke** (`_smoke_pids/fernet.key`),
  injetada pelo target via `SMOKE_FERNET_KEY`. Sem ela a hidratação
  (config_materializer/vault) falha com 503 nomeando ADR-303 D4 — sintoma:
  gate para no POST.
- **Imagem cresce** (lock inteiro do backend, `--require-hashes`). Aceito:
  uso é smoke opt-in; produção segue `InProcessPipelineClient`. Se um dia
  esta imagem for a prod, revisitar multi-stage (ver
  [docker_images.md](docker_images.md)).

## 4. Verificação manual (sem o gate)

```bash
curl --max-time 10 http://localhost:8001/health
docker exec -i mathoms-pipeline-service python - <<'EOF'
import sqlite3
c = sqlite3.connect("/repo/mathoms-smoke.db")
print(c.execute("select stage, artifact_key, pipeline_run_id from pipeline_artifacts order by rowid desc limit 5").fetchall())
EOF
docker logs mathoms-pipeline-service --tail 20   # logs JSON (MATHOMS_LOG_FORMAT=json)
```

## 5. Cleanup

`make smoke-pipeline-service-down` remove o container (a imagem fica para
cache de build). Artefatos de smoke (`mathoms-smoke.db`, `_smoke_storage/`,
`_smoke_pids/`) são gitignored; `make smoke-reset` zera tudo — rode antes de
um novo ciclo se quiser gate limpo (DB stale = falso-positivo de "artefato
apareceu" do run anterior).

## 6. Dogfood com o shell Go (F2 — pré-cutover)

O caminho mais simples para validar o executor Go com dados reais:

```bash
make smoke-up                          # stack normal (worker Python in-process)
export ANTHROPIC_API_KEY=...           # stages LLM rodam no subprocess do Go
make dogfood-go                        # builda + sobe shell Go :8002 + re-aponta o worker
# ... rode o pipeline pela UI e valide o relatório (gate humano ADR-150 §7)
make dogfood-go-off                    # rollback: worker volta ao executor Python
```

O Celery continua orquestrando (cancel, needs_review, lineage); só a
execução de cada stage passa pelo shell Go via HTTP (binário no HOST —
sem a restrição de WAL do container). Overhead esperado: ~550ms/stage de
boot do subprocess. Logs: `_smoke_pids/go.log` + `worker.log`.

### 6.1 Variante DEV — workspace real

Para testar o Go contra o ambiente dev de verdade (mesmo `.env`, mesmo DB,
mesmos documentos já uploadados — sem re-seed):

```bash
make dev-up                            # stack dev normal, se ainda não estiver de pé
make dogfood-go-dev                    # shell Go :8002 com env do .env + worker dev re-apontado
# ... rode o pipeline pela UI dev (localhost:3000) no seu workspace real
make dogfood-go-dev-off                # rollback: worker dev volta ao executor Python
```

O target carrega o `.env` da raiz para o env do binário Go — o subprocess
`python -m pipeline.orchestrator run-stage` herda dele `MATHOMS_DATABASE_URL`,
`MATHOMS_FERNET_KEY`, `MATHOMS_REDIS_URL` e `ANTHROPIC_API_KEY` (aviso se
ausente). O worker re-sobe com hostname `celery-dev-go@…` para distinguir
nos logs. Logs: `_dev_pids/go.log` + `worker.log`.
