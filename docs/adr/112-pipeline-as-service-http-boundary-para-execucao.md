---
id: ADR-112
type: adr
title: "Pipeline-as-Service: HTTP boundary para execução de stages (A6f.1)"
status: Decidido
phase: "A6f.1"
date: "2026-04-21"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 112"]
tags:
  - type/adr
  - status/decidido
size_lines: 89
---

# ADR-112 — Pipeline-as-Service: HTTP boundary para execução de stages (A6f.1)

**Status:** Decidido (A6f.1) • **Data:** 2026-04-21

**Contexto:** Até A6e, `backend/app/tasks/pipeline_task.py` importava
`pipeline.orchestrator._run_stage` diretamente para executar cada stage
dentro do worker Celery. Isso acoplava o ciclo de vida do pipeline ao
processo Python do backend: qualquer refactor de orquestração obrigava a
reiniciar o worker, e a fronteira language-neutral que ADR-102 R18 pede
(clientes não-Python conseguirem falar com o pipeline) continuava
imaginária. A6e.1–.4 fecharam per-aggregate repos/DTOs; A6f.2/.3/.4/.5a/.6
destravaram OpenAPI snapshot, logs JSON, schema DB neutro e gate
empírico de multi-worker. O degrau restante era a execução de pipeline.

Duas opções consideradas:

1. **Subprocess/Celery task dedicado** — pipeline continua in-tree mas
   roda em worker separado. Ganho de isolamento, zero ganho de
   portabilidade (ainda Python-to-Python via broker).
2. **HTTP service standalone** — pipeline-service expõe REST+WS. Qualquer
   consumidor (Go futuro, CLI externo, script de staging) fala contrato
   documentado. Cutover gradual via feature flag.

**Decisão:** implementar a opção 2. Nasce `pipeline-service/` (FastAPI
greenfield) expondo `POST /api/v1/pipeline/runs`,
`POST /api/v1/pipeline/stages/{stage}/execute` e WS
`/api/v1/pipeline/events/{run_id}`. Backend consome via
`PipelineServiceClient` (Protocol) com duas implementações: `HttpPipelineClient`
quando `MATHOMS_PIPELINE_SERVICE_URL` está setada, `InProcessPipelineClient`
caso contrário (dev, test, single-process deploy). A flag é env var — não
config de app — para permitir cutover por ambiente sem redeploy do
backend.

Pipeline-service é **stateless rigoroso** (ADR-111): zero DB, zero cache
por-request, Redis singleton lazy+idempotente. Artefatos atravessam a
fronteira por `workspace_root` (path em disco) — backend permanece dono
do `DBArtifactStore`; pipeline-service opera com o `DiskArtifactStore`
que vê em disco, sem consultar DB. Isso mantém a fronteira fina e torna
trivial rodar múltiplas instâncias do pipeline-service atrás de um LB.

Não é migração para Go ainda. ADR-112 define o **contrato**; a
substituição da implementação Python por Go é uma A6f seguinte, sem
mudança de wire format.

**Consequências:**

- ✅ Fronteira language-neutral real — OpenAPI snapshot em
  `docs/reference/api/v1/pipeline-service.openapi.json` é fonte de verdade; qualquer
  cliente pode consumir.
- ✅ `backend/app/tasks/pipeline_task.py` zero `from pipeline.orchestrator`
  imports — gate enforçável por grep + revisão de PR.
- ✅ `InProcessPipelineClient` evita regressão: ambiente atual (sem
  `MATHOMS_PIPELINE_SERVICE_URL`) roda idêntico. Test suite inteira
  valida ambos os clients.
- ✅ Redis pub/sub preserva compat com `backend/app/services/events.py` —
  mesmo envelope, mesmo canal, WS do backend continua funcionando
  durante transição.
- ⚠️ Um processo a mais no deploy. Em smoke local, `docker-compose.pipeline-service.yml`
  sobe junto. Em prod, cutover exige orquestração (K8s manifest, ECS
  service, etc.) — escopo de A6-deploy, não A6f.1.
- ⚠️ Overhead HTTP por stage: serialização JSON + round-trip ~2–5ms em
  rede local. Irrelevante frente aos minutos que stages reais levam
  (E3/E5), mas registrar para comparações futuras.
- ❌ Duplicação mínima de DTOs (Pydantic em `pipeline-service/app/contracts/`
  espelhando `backend/app/schemas/pipeline.py`). Aceito porque cada lado
  publica seu próprio OpenAPI; manter em sync é responsabilidade dos
  snapshot tests (ambos falham se contrato diverge sem intenção).

**Escopo deferido (follow-ups explícitos):**

- Extração de helpers (`_materialize_adapter_configs`,
  `_persist_llm_suggestions`, `_create_report_from_output`) de
  `pipeline_task.py` para services dedicados e redução do arquivo para
  ≤100 linhas — refactor comportamento-preservante, slice próprio.
- Migração do backend para usar `HttpPipelineClient` por default em
  staging (flip do env var nos pipelines CI/CD). Gate humano.
- Go rewrite do pipeline-service (A6f seguinte). Contrato HTTP fixo
  permite rodar ambas as implementações atrás do mesmo LB.

**Artefatos:**

- `pipeline-service/app/**` — FastAPI app, contratos, services.
- `backend/app/services/pipeline_client.py` — Protocol + 2 implementações.
- `docs/reference/api/v1/pipeline-service.openapi.json` — snapshot do contrato.
- `docker-compose.pipeline-service.yml` — compose overlay para smoke.
- `Makefile` — `update-pipeline-service-openapi` target e composição
  automática com `update-openapi-snapshot`.
