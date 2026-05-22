---
id: ADR-256
type: adr
title: "Stages do pipeline compartilham unit-of-work via `WorkspaceContext.get_artifact_store().session`"
status: Decidido
phase: A19.uow-stages
date: "2026-05-22"
relates_to:
  - "[[ADR-111]]"
  - "[[ADR-212]]"
  - "[[ADR-089]]"
  - "[[ADR-097]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 256"
  - "Unit-of-work stages"
  - "No parallel SyncSessionLocal"
tags:
  - area/pipeline
  - area/backend
  - area/persistence
  - status/decidido
  - type/adr
---

# ADR-256 — Stages do pipeline compartilham unit-of-work via `store.session`

**Status:** Decidido (A19.uow-stages) • **Data:** 2026-05-22 • **Relaciona** [[ADR-111]] (stateless-rigoroso), [[ADR-212]] (DBArtifactStore DB-only), [[ADR-089]]/[[ADR-097]] (services recebem config tipado, não `Session`).

## Contexto

Em 2026-05 dois incidentes prod tiveram a mesma causa-raiz: **um stage do pipeline abria `SyncSessionLocal()` paralela à session per-stage injetada pelo orchestrator** ([backend/app/tasks/pipeline_task.py:860](../../backend/app/tasks/pipeline_task.py) `_open_artifact_session`).

| Data | Stage / serviço | Sintoma | PR fix |
|---|---|---|---|
| 2026-05-18 (run `dadb0cd6`) | `DBPropertyIdentityResolver` em E5 | `database is locked` em INSERT `pipeline_artifacts` paralelo | [tests/unit/pipeline/test_property_identity_enricher.py:191](../../tests/unit/pipeline/test_property_identity_enricher.py) |
| 2026-05-22 (workspace `1b9f2cf5-...`) | `extract_comprovantes_bens` | `database is locked` em INSERT `vehicles` após 30s `busy_timeout` | [#443](https://github.com/davidrobert/mathoms/pull/443) |

**Mecanismo idêntico em ambos:**

1. Stage chama `ctx.get_artifact_store().write(stage, key, payload)`.
2. `DBArtifactStore.write` ([backend/app/services/db_artifact_store.py:248](../../backend/app/services/db_artifact_store.py)) faz `self._session.add(...)`. O `_get()` interno (consultado pela `write` para decidir insert vs. update) dispara **autoflush** — `stage_session` adquire o write-lock SQLite e o retém até `_commit_and_close_artifact_session` no fim do stage.
3. Stage chama `SyncSessionLocal()` paralela para outra tabela (vehicles, property_identity), abre nova conexão do pool, tenta `flush()+commit()`.
4. SQLite (mesmo em WAL) serializa writes via lock global. Segunda conexão espera `busy_timeout=30s` e estoura `OperationalError: database is locked`.

A correção pontual em cada incidente foi **reusar a `store.session`** via parâmetro kwarg-only (`db: Session`). Mas o padrão "session paralela acidental" reincidiu 2× em 4 dias — comentário no código + teste de regressão local não impedem o **próximo** stage novo de cair no mesmo buraco.

### Por que isso é arquitetural, não estilístico

- **Correção semântica:** `store.write(...)` + INSERT em outra tabela na mesma "unidade lógica de trabalho" devem participar do **mesmo commit atômico**. Hoje, se o upsert paralelo commita primeiro e o stage_session faz rollback depois (erro tardio), a tabela auxiliar fica com row órfã referenciando artifact inexistente. Inverso também ocorre.
- **Read-your-writes:** Postgres futuro (F7) tem read-committed isolation; uma session paralela **não** vê o que outra ainda não commitou — quebra silenciosamente leituras feitas por callees do stage.
- **Escalabilidade:** SQLite hoje serializa; Postgres amanhã permite, mas o invariante de UoW único por stage é o que mantém consistência sob qualquer engine.

## Alternativas consideradas

1. **Não formalizar** (status quo). Risco já materializado 2×; com Postgres no horizonte, terceira ocorrência vira corrupção silenciosa em vez de erro óbvio. Descartada.
2. **Comentário no `DBArtifactStore.session` property + teste de regressão local.** É o que existe hoje após PR #443 e não impediu reincidência. Descartada.
3. **Gate de pre-commit (`dev/check_pipeline_sessions.py`)** complementando [dev/check_pipeline_boundaries.py](../../dev/check_pipeline_boundaries.py) (que já bloqueia `fastapi`/`celery`/`sqlalchemy` em `pipeline/**`). Custo: ~50ms por hook run, 1 arquivo novo. Cobre 100% do código futuro. **Escolhida.**
4. **Lint custom AST mais elaborado** (procurar `Session(...)` aberto fora de contexto de DI). Descartada por ora — regex line-based já cobre os patterns reais; AST agrega complexidade sem ganho mensurável.
5. **Mover stages para receber `Session` em assinatura explícita** (`def run(ctx, *, db)` em vez de `def run(ctx)`). Tentadora mas duplica injeção — `ctx.get_artifact_store().session` já é a fonte única. Descartada.

## Decisão

1. **Invariante.** Stages em `pipeline/stages/**` e serviços de domínio em `pipeline/domain/**` **não instanciam `Session` própria**. Quando precisam de DB:
   - **Padrão A (preferido):** consomem `ctx.get_artifact_store().session` (já é o `Session` injetado pelo orchestrator per-stage).
   - **Padrão B (services standalone):** recebem `db: Session` por parâmetro kwarg-only e o caller injeta. Modelo: [pipeline/stages/extract_comprovantes_bens.py:307 `_upsert_in_db`](../../pipeline/stages/extract_comprovantes_bens.py) (pós-#443).

2. **Gate.** `dev/check_pipeline_sessions.py` (pre-commit + CI) bloqueia em `pipeline/**/*.py`:
   - `SyncSessionLocal`, `AsyncSessionLocal`
   - `async_session(`, `Session(` (import direto do SQLAlchemy)
   - `sessionmaker(`, `scoped_session(`
   - import de `backend.app.core.database` (que expõe as factories)

   Whitelist explícita: arquivos de teste (`tests/**`, `backend/tests/**`) e o próprio `WorkspaceContext` (se algum dia hospedar a injeção).

3. **Instrumentação.** Contador `mathoms.db.lock_retry_count` no `DBArtifactStore.write`/`_get` (captura retries do `busy_timeout` SQLite quando ele acontece — sinal precoce de contenção persistente). Sem esse counter, decidir migrar para Postgres ([critério Postgres trigger]) vira anedótico.

4. **ADR-256 flippa para `Decidido (Sprint A19)` no merge do PR que entrega gate + counter.**

## Consequências

**Positivas:**

- Elimina classe inteira de `database is locked` originada de stages.
- Writes do stage participam do mesmo commit atômico (read-your-writes coerente).
- Migração F7 (Postgres) herda comportamento correto sem refactor adicional.
- Próximo agente que tentar `SyncSessionLocal()` em `pipeline/**` é bloqueado **antes** do commit; recebe mensagem do gate apontando para esta ADR.

**Negativas / custo:**

- Gate adicional no pre-commit (~50ms). Total dos hooks atuais ~3s; impacto irrelevante.
- Stages que precisem de session **fora** do escopo do artifact_store devem refatorar para receber `db` por parâmetro — hoje só o `extract_comprovantes_bens` (já em #443); auditoria futura pode pegar mais.
- Falso-positivo possível se `WorkspaceContext` for movido para `pipeline/` — mitigado pela whitelist do gate.

**Não-objetivos:**

- Esta ADR **não** decide migração SQLite → Postgres. Critérios de gatilho ficam em issue rastreável separada (custo de antecipar é alto; sem dados de produção pós-#443, decisão é prematura).
- Esta ADR **não** redefine como o orchestrator gerencia stage_session — [pipeline_task._execute_stages_loop](../../backend/app/tasks/pipeline_task.py) já abre/commita per-stage desde 2026-04-23 (incidente Celery lock). Apenas formaliza o invariante do consumidor.

## Plano de execução

1. **PR 1 (esta ADR):** doc-only, `Proposto`. Merge rápido sem CI gate (regra docs-only do CLAUDE.md).
2. **PR 2:** `dev/check_pipeline_sessions.py` + entrada em `.pre-commit-config.yaml` + counter `lock_retry_count` em `DBArtifactStore` + audit `STATELESS_AUDIT.md` style document **OU** comentário in-place. ADR-256 flippa para `Decidido (Sprint A19)`. Estado verde no merge: zero ocorrências em `pipeline/**` (já garantido por #443).
3. **Issue rastreável (sem PR):** "Postgres migration trigger criteria" com gatilhos do senior-cto — recorrência ≥1 em 90d pós-#443, decisão de subir `worker_concurrency ≥ 4`, >50 workspaces ativos OR p95 stage-write >5s sustentado 1 semana, paralelizar E2 por banco.

## Auditoria preliminar (2026-05-22, pré-PR 2)

Após #443, ocorrências de `SyncSessionLocal` em `pipeline/**`: **0** (`rg -n SyncSessionLocal pipeline/`). Gate nasce em estado verde.

Ocorrências legítimas fora de `pipeline/**` (whitelist implícita do gate):

- `backend/app/services/*.py` — services internos do backend (pipeline_service, config_materializer, document_extract_json_service, document_pipeline_sync, artifact_reader). **Não rodam dentro de stage.**
- `backend/app/tasks/*.py` — orchestrator Celery (`pipeline_task.py`) + Beat schedules (`periodic_tasks.py`, `fipe_refresh.py`, `lgpd_export.py`). **`pipeline_task.py` é quem injeta a session; demais não tocam tabelas escritas por stage do mesmo workspace concorrente.**
- `backend/scripts/`, `backend/app/scripts/` — CLI scripts standalone (backfill, seed, smoke). **Não rodam em runtime de stage.**
