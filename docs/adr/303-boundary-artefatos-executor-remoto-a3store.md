---
id: ADR-303
type: adr
title: "Boundary de artefatos do executor remoto (A3.store): pipeline-service injeta DBArtifactStore do backend, sessão-por-stage"
status: Decidido
phase: "A3.store — fix do modo HTTP do pipeline-service"
date: "2026-07-03"
relates_to:
  - "[[ADR-112]]"
  - "[[ADR-150]]"
  - "[[ADR-205]]"
  - "[[ADR-212]]"
  - "[[ADR-241]]"
  - "[[ADR-256]]"
  - "[[ADR-291]]"
aliases:
  - "ADR 303"
  - "A3.store"
tags:
  - area/pipeline
  - area/architecture
  - status/decidido
  - type/adr
size_lines: 128
---

# ADR-303 — Boundary de artefatos do executor remoto (A3.store)

**Status:** Decidido (A3.store — fix do modo HTTP) • **Data:** 2026-07-03

## Contexto

- [[ADR-212]] tornou `pipeline_artifacts` (DB, via `DBArtifactStore`) o único
  caminho de leitura/escrita de artefatos e deletou `DiskArtifactStore`;
  `WorkspaceContext.get_artifact_store()` raise `RuntimeError` sem injeção.
- O modo HTTP do `pipeline-service` ([[ADR-112]]) constrói
  `WorkspaceContext.for_tenant(...)` **sem injetar store** — qualquer stage
  que toque artefato (19 call-sites) quebra. Bug latente: produção usa
  `InProcessPipelineClient`/Celery (que injeta via `_open_artifact_session`,
  `backend/app/tasks/pipeline_task.py`); o serviço só sobe em overlay de
  smoke opt-in, e o baseline A2 media só `/health`.
- **Agravante:** a suíte `pipeline-service/tests/` não roda em nenhum
  workflow de CI — o path podia quebrar (e quebrou) em silêncio.
- A emenda 2026-07-02 da [[ADR-150]] registrou A3.store como primeiro
  pré-requisito do port Go (Caminho 1) e pediu esta ADR.

## Alternativas consideradas

1. **Executor injeta `DBArtifactStore` próprio** (sessão SQLAlchemy dedicada
   por-stage, contra `DATABASE_URL`, importando a classe do backend).
   Replica o padrão validado em produção pelo Celery; contrato HTTP segue
   só-comando. **Aceita.**
2. **Contrato HTTP transporta artefatos** (backend hidrata inputs no request,
   coleta outputs no response). Rejeitada: os fallbacks de leitura
   workspace-scoped ([[ADR-241]]) e run-pinado ([[ADR-291]]) tornam a
   pré-hidratação incomputável sem executar o stage; payloads E4/E5 chegam
   a MBs; quebra a fronteira fina de [[ADR-112]] e a estabilidade de
   contrato de [[ADR-205]] D2.
3. **Store remoto via API do backend.** Rejeitada: dezenas de round-trips
   por run (E3 lê N extratos; E4 escreve 7 keys) + duplicação do contrato
   de validação no cliente ou no servidor.

## Decisão

### D1. Injeção do `DBArtifactStore` do backend, sessão-por-stage

O executor remoto (pipeline-service hoje; subprocess do A3.cli no futuro)
abre, **por stage**, sessão nova + `DBArtifactStore` e injeta em
`ctx.artifact_store`, com commit/rollback/close ao fim do stage — espelho de
`_open_artifact_session` / `_commit_and_close_artifact_session` do caminho
Celery. **Importa a classe `backend.app.services.storage.db_artifact_store.DBArtifactStore`
— nunca reimplementa**: o hook de validação `SCHEMA_BY_STAGE` e a
criptografia vivem no `write()`; reimplementação silenciosamente não valida.
`pipeline-service/**` está fora do import-ban de
`dev/check_pipeline_boundaries.py` (que cobre só `pipeline/**`).

### D2. Delta aditivo de contrato

`StageExecuteRequest` e `RunStartRequest` ganham `base_run_id: str | None` e
`base_run_fallback_stages: list[str]` (defaults preservam full/incremental).
Sem eles, from_stage ([[ADR-291]]) quebra no modo HTTP. Campos opcionais —
não-breaking; snapshot OpenAPI regenerado no mesmo PR.

### D3. Invariantes de separação de responsabilidade

- **Lineage e telemetria de run** ([[ADR-279]]/[[ADR-293]]) permanecem no
  orquestrador backend, pós-execução — não migram para o executor.
- **Validação de schema + crypto** permanecem no `write()` do store.
- **Tenancy por construção:** o store é scoped por `workspace_id` +
  `pipeline_run_id` vindos do request; toda query filtra por eles. O
  executor confia no backend chamador (rede interna, sem exposição pública
  — [[ADR-112]]).
- **Unicidade/concorrência:** constraint `uq_pipeline_artifacts_run_stage_key`
  (`pipeline_run_id, stage, artifact_key`) + invariante "um `run_id` é
  executado por um único executor por vez" (RunCoordinator sequencia).

### D4. Fail-fast com mensagem clara

Se `backend` não for importável ou o DB não estiver configurado, o executor
falha **no início do stage** com erro estruturado nomeando a causa e esta
ADR — nunca `RuntimeError` opaco no meio do stage.

### D5. Suíte do pipeline-service entra no CI

`pytest pipeline-service/tests -q` passa a rodar em PR. O teste de
integração canônico exercita um stage real (`reconcile_transactions`) via
HTTP com store SQLite, assertando persistência em `pipeline_artifacts`.

## Escopo deferido — ✅ fechado em 2026-07-03

- **Enablement do container/compose smoke** — ✅ **entregue (PR #743)**: a
  imagem instala `requirements.lock` (`--require-hashes`) + copia
  `backend/scripts/config`; overlay compartilha o SQLite do smoke +
  fernet key; gate `make smoke-pipeline-service` executa stage real via
  HTTP e prova persistência (runbook:
  [pipeline_service_container_smoke](../reference/runbooks/pipeline_service_container_smoke.md)
  — inclui a restrição SQLite WAL host↔container descoberta na entrega).
- **Paridade de hidratação de contexto** — ✅ **entregue (PR #742)**:
  `backend/app/services/pipeline/run_context_factory.py` é a fonte única dos três
  executores (Celery/HTTP/CLI) — `DBConfigStore` + overrides, resolvers
  (ADR-215/219/222), budget hooks (ADR-173) e `tarefas.md`. A
  pré-condição do gate de paridade da [[ADR-150]] §7 está satisfeita.

## Consequências

- ✅ Modo HTTP volta a funcionar e ganha teste que impede regressão muda.
- ✅ A3.cli (CLI do orchestrator) herda a mesma mecânica de injeção.
- ⚠️ `pipeline-service` ganha segundo acoplamento ao `backend/` (o primeiro,
  `setup_logging`, é opcional; este é hard para executar stages) e, no
  deploy futuro, dependência de Postgres (credencial + pool pequeno).
  Registrado em [GO_PORT_DEPS.md](../reference/GO_PORT_DEPS.md) §5.6.
- ⚠️ Dois produtores de escrita em `pipeline_artifacts` (backend Celery e
  executor remoto) — mitigado por D3 (mesma classe, constraint, run único).
