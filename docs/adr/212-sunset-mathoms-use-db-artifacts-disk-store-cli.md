---
id: ADR-212
type: adr
title: "Sunset `MATHOMS_USE_DB_ARTIFACTS` + `DiskArtifactStore` + CLI standalone do pipeline"
status: Decidido
phase: A12.sunset-disk-artifact
date: "2026-05-14"
relates_to:
  - "[[ADR-083]]"
  - "[[ADR-120]]"
  - "[[ADR-129]]"
  - "[[ADR-211]]"
  - "[[ADR-111]]"
  - "[[ADR-116]]"
supersedes:
  - "[[ADR-118]]"
  - "[[ADR-106]]"
superseded_by: []
aliases: ["ADR 212", "sunset disk artifact store", "DB-only artifacts"]
tags:
  - area/backend
  - area/pipeline
  - area/ops
  - phase/a12
  - status/decidido
  - type/adr
---

## Contexto

O cutover de `ArtifactStore` para DB está estável há mais de um ano:
ADR-083 (introduziu a abstração), ADR-106 (opt-in por workspace),
ADR-118 (flip do default para `True` em 2026-04-23), ADR-120 (readers
user-facing DB-first com fallback de disco). Todos os workspaces de
produção rodam com `MATHOMS_USE_DB_ARTIFACTS=true`. O caminho `False`
nunca foi acionado em produção desde o flip; CI roda apenas em modo DB
desde A6b.flip.2.

O que ficou de débito conservador:

1. **Flag `settings.USE_DB_ARTIFACTS`** e coluna
   `workspaces.use_db_artifacts_override: bool | None` continuam
   resolvidas a cada run em `_resolve_use_db_artifacts(ws_id)`
   ([backend/app/tasks/pipeline_task.py:394](../../backend/app/tasks/pipeline_task.py)).
   Default é `True`, override nunca é setado em produção.

2. **`DiskArtifactStore`** (~150 das 321 linhas em
   [pipeline/artifact_store.py](../../pipeline/artifact_store.py)) é o
   default de `WorkspaceContext.get_artifact_store()`
   ([pipeline/context.py:127](../../pipeline/context.py)). Toda lib que
   instancia `WorkspaceContext` sem injetar store explícita roda em
   modo disco — defesa por inércia que mascara bugs em vez de prevenir.

3. **30+ arquivos** com branches `if use_db_artifacts:` /
   `if isinstance(store, DiskArtifactStore):`. Examples:
   - [backend/app/services/document_extract_json_service.py:58](../../backend/app/services/document_extract_json_service.py) — fallback DB para E1.5
   - [backend/app/services/document_pipeline_sync.py:78](../../backend/app/services/document_pipeline_sync.py) — fallback DB para E1.5a
   - [backend/app/services/artifact_reader.py](../../backend/app/services/artifact_reader.py) — DB-first com fallback disco (ADR-120)
   - [pipeline/stages/extract_with_llm.py:255](../../pipeline/stages/extract_with_llm.py) — validação JSON-schema condicional
   - `scripts/e3_reconcile.py`, `scripts/e4_categorize.py`,
     `scripts/e5_analyze.py` — `isinstance(store, DiskArtifactStore)`
     em pontos de serialização.

4. **CLI standalone do pipeline** — entrypoints `if __name__ == "__main__"`
   em 5 dos 11 scripts (`e0_audit`, `e0_unlock`, `e0_route`,
   `e2_extract`, `e_reset`). Os outros 6 (`e3_reconcile`,
   `e4_categorize`, `e5_analyze`, `e7_review`, `e5n_narrativas`,
   `e15_consolidate`) já perderam o `__main__` em refactors anteriores —
   viraram libraries lazy-importadas por `pipeline/stages/*.py`. Os
   scripts continuam sendo a implementação canônica de cada stage, mas
   "rodar pipeline inteiro via CLI sem backend" é capacidade dead — git
   log dos últimos 6 meses não mostra uso real. Documentação em
   [docs/reference/SETUP.md:344](../../docs/reference/SETUP.md) §8 ainda
   convida a esse caminho.

5. **Runbook de rollback** ADR-118 (`MATHOMS_USE_DB_ARTIFACTS=false` +
   redeploy) nunca foi exercitado em produção. ADR-120 §Alternativas
   rejeitou "remover disco inteiramente" porque "quebra CLI dev,
   DiskArtifactStore e workflows que hoje editam JSONs à mão. Rollback
   do ADR-118 fica inviável" — argumento operacional baseado em estado
   de A6 (cutover recente). Um ano depois, "editar JSONs à mão" não é
   workflow ativo e rollback flip-flag tem alternativa mais robusta
   (snapshot DB + revert da migration).

6. **Métricas Prometheus prescritas em
   [docs/reference/runbooks/cutover.md §2.5](../archive/cutover-2026-05-14.md)
   nunca foram implementadas** — `pipeline_run_duration_seconds{store}`,
   `artifact_diff_count`, `pipeline_run_failed_total{use_db}` eram
   débito de F7C (observabilidade), nunca shipped. O runbook é
   aspiracional; o observabilidade de produção hoje é
   `mathoms.pipeline` logs estruturados (ADR-110) + métricas básicas
   FastAPI. **Consequência:** não há série Prometheus a aposentar
   junto com PR4 — só logs e referências em runbook arquivado.

7. **ADR-211 §Não-objetivos lane 3** ("Deletar
   `prepare_pipeline_config_dir` por completo") está **bloqueada por
   CLI standalone**. Esta ADR remove o bloqueio.

## Decisão

Remover **completamente** o caminho `DiskArtifactStore` em produção e
descontinuar o CLI standalone do pipeline. Cinco entregas em PRs
sequenciais (ordem revisada em revisão multi-especialista 2026-05-14:
PR2 antes de PR1 para reduzir risco de regressão silenciosa em boot);
cada PR é independentemente revertível via `git revert`.

### Premissa explícita: Postgres-only em produção

`pipeline_artifacts` em SQLite usa write-lock global — multi-worker
Celery em SQLite contende. **Produção exige Postgres** desde A6f; SQLite
é dev-only. PR3 expõe contenção que `DiskArtifactStore` mascarava em
deploys self-hosted hipotéticos rodando SQLite — não há nenhum em
2026-05-14, mas a premissa é gate para qualquer self-hosted futuro.

### PR2 (primeiro) — Coletar isenções `MATHOMS_WORKSPACE_ROOT` (~0.5 dia)

Inverter ordem original (PR2 antes de PR1, conforme review senior-cto):
primeiro remover a defesa, e se algo quebra, o sintoma aparece **antes**
de deletar entrypoints CLI.

- Remover `os.environ["MATHOMS_WORKSPACE_ROOT"] = ...` de
  [backend/app/tasks/pipeline_task.py:500](../../backend/app/tasks/pipeline_task.py)
  — `pipeline_common.py` já recebe paths via `WorkspaceContext`.
- Remover `setdefault` em [backend/app/worker.py:25](../../backend/app/worker.py)
  e [backend/app/main.py:8](../../backend/app/main.py) — sem CLI
  importando `pipeline_common` no boot, a defesa não tem alvo.
- Manter `setdefault` em `conftest.py` (testes ainda fazem setup
  explícito; aceitável).

**Gate:** `make dev` sobe limpo; suíte verde sem mudanças;
`grep -rn "MATHOMS_WORKSPACE_ROOT" backend/` retorna 0.

### PR1 — Remover entrypoints CLI mortos + extrair service-layer (~1 dia)

- Deletar `if __name__ == "__main__"` + funções `main()` de:
  - `scripts/e0_route.py`
  - `scripts/e0_unlock.py`
  - `scripts/e2_extract.py`
- Manter os módulos como libraries (continuam importados por
  `pipeline/stages/*.py`).
- **Deletar `scripts/e_reset.py` (1406 linhas) mas extrair função
  reusável** `reset_workspace_from_stage(db, ws_id, from_stage, *,
  dry_run=True, move_to_inbox=False) -> ResetPreview` em
  `backend/app/services/internal_ops/pipeline_reset.py` — camada IA-0
  do console interno (ADR-116). Endpoint HTTP **NÃO** é criado neste
  ADR — depende de IA-1 (auth staff + audit persistido + IP allowlist).
  Pré-IA-1, ops usa o service-layer via console interno local-only
  (bind 127.0.0.1) ou via Python shell em emergência. Endpoint público
  vira lane separada em [docs/plan/INTERNAL_ADMIN/_README.md](../plan/INTERNAL_ADMIN/_README.md).
- **Manter** `scripts/e0_audit.py` (read-only, inspeção de filesystem
  legítima — sem ArtifactStore envolvido).
- Atualizar [docs/reference/SETUP.md](../../docs/reference/SETUP.md) §8
  removendo bloco CLI; substituir por "Pipeline roda exclusivamente
  via backend (Celery worker). Para debug local, suba `make dev` e
  use `POST /pipeline/run`."
- Atualizar [docs/reference/SMOKE_TEST_HUMAN.md:209](../../docs/reference/SMOKE_TEST_HUMAN.md)
  trocando `python scripts/e_reset.py --from E3 --dry-run` por
  invocação direta de `reset_workspace_from_stage` via console interno.

**Gate:** `grep -rn "if __name__" scripts/` retorna só `e0_audit.py`.
Testes verdes. `internal_ops/pipeline_reset.py` tem teste unitário
com `InMemoryArtifactStore`.

### PR1.5 — Runbook `pipeline_rollback.md` (~0.5 dia)

**Pré-requisito de PR3** (sre-devops P0). ADR-118 §Rollback referenciava
"setar flag + redeploy" como procedimento operacional. Pós-PR3 essa
opção morre; nova estratégia precisa runbook canônico antes de PR3
subir, não depois.

Criar `docs/reference/runbooks/pipeline_rollback.md` com:

1. **Detecção** — gatilhos que disparam rollback (anomalia em logs
   `mathoms.pipeline`, falha em ≥5% de runs em 1h via query SQL ad-hoc
   sobre `pipeline_runs`, corrupção em `pipeline_artifacts.content_json`).
2. **Snapshot pré-deploy** — gate obrigatório, não opcional:
   `pg_dump --table=pipeline_artifacts --table=workspaces
   --table=pipeline_runs --table=pipeline_stage_logs > snap.sql`
   antes de qualquer deploy que toque schema ou stages.
3. **Decision tree:**
   - Corrupção localizada (1 workspace) → restore por workspace via
     `DELETE FROM pipeline_artifacts WHERE workspace_id=? AND
     pipeline_run_id IN (...)` + `COPY` do snapshot.
   - Regressão global (>5% runs failed) → revert PR + restore
     `pipeline_artifacts` inteira.
   - Bug determinístico (conteúdo errado, sem corrupção) → fix-forward.
4. **Validação pós-rollback** — smoke test em workspace canário,
   30min de observação antes de unfreeze.
5. **Documentar janela RTO/RPO** — 30min RTO (vs 5min do flip-flag),
   RPO ≤24h (depende de cadência de snapshot).

**Gate:** runbook revisado pelo oncall do owner; smoke test do
procedure executado em staging.

### PR3 — Deletar `DiskArtifactStore` + cleanup de branches (~2-3 dias)

- **Deletar classe `DiskArtifactStore`** + funções auxiliares em
  [pipeline/artifact_store.py](../../pipeline/artifact_store.py)
  (~150 linhas). **Manter** `ArtifactStore` protocol e
  `InMemoryArtifactStore` (este último é fake testável obrigatório
  em `tests/`, sem dependência de DB — preserva ADR-083 §Testabilidade).
- **`pipeline/context.py` — `WorkspaceContext.__init__` aceita
  `artifact_store: ArtifactStore` como parâmetro obrigatório**
  (recomendação convergente senior-cto + data-engineer). Substitui
  padrão "instancia default + raise tardio em get". Falha em tempo
  de construção, com tipo. Custo: ~1 dia de refactor em callers de
  `WorkspaceContext.for_tenant` que omitem store; ganho: invariante
  checada por type checker (mypy/pyright), não por exceção tardia em
  runtime.
- Remover branches `if isinstance(store, DiskArtifactStore):` em:
  - `scripts/e3_reconcile.py:1087,1179`
  - `scripts/e4_categorize.py:1081`
  - `scripts/e5_analyze.py:3051`
  - `pipeline/stages/extract_with_llm.py:261`
  - Manter o lado "DB" do branch; deletar lado "disk".
- **Validação JSON-schema** ([pipeline/stages/extract_with_llm.py:259](../../pipeline/stages/extract_with_llm.py))
  — **mover para hook pós-write em `DBArtifactStore.write`**
  (decisão convergente senior-cto + data-engineer; não aceitar perda).
  Mapping `SCHEMA_BY_STAGE` (~5 entradas: E1.5, E2, E4, E5, pipeline)
  + modo `strict|warn` herdado de `pipeline.json`. Hook é ~15 linhas:
  ```python
  def write(self, stage, key, data, *, document_id=None):
      schema_file = SCHEMA_BY_STAGE.get(stage)
      if schema_file and settings.SCHEMA_VALIDATION_STRICT:
          validate_dict(data, schema_file)  # raise se inválido
      # ... persist
  ```
- Deletar fallback de disco em
  [backend/app/services/artifact_reader.py](../../backend/app/services/artifact_reader.py)
  (`read_latest_artifact`) — DB-only. Decisão de ADR-120 (DB-first com
  fallback) fica obsoleta no que diz respeito ao fallback;
  consideração DB-first preservada.
- **Deletar `backend/app/scripts/backfill_artifacts_from_disk.py`** —
  importa `_STAGE_TO_DIR` do disk store; sem alvo após PR3
  (data-engineer P0).
- **Deletar `dev/compare_disk_vs_db.py`** — confirmado 0 referências em
  `.github/workflows/` (sre-devops); paridade disk-vs-db deixa de
  existir.
- Deletar `_resolve_use_db_artifacts` + chamada em
  [backend/app/tasks/pipeline_task.py:394](../../backend/app/tasks/pipeline_task.py).
  Celery task sempre instancia `DBArtifactStore`.
- **Refatorar goldens de execução**
  ([tests/test_e3_golden_execution.py](../../tests/test_e3_golden_execution.py),
  `test_e4_golden_execution.py`, `test_e5_golden_execution.py`) para
  injetar `InMemoryArtifactStore` via construtor explícito de
  `WorkspaceContext` (data-engineer P0; F.I.R.S.T preservado, ~100x
  mais rápido que sqlite-memory + ORM). DB-real em sqlite-memory fica
  reservado para integration tests em `backend/tests/integration/`.
- Limpar log `pipeline_start using DBArtifactStore for run_id=...` em
  [backend/app/tasks/pipeline_task.py:480](../../backend/app/tasks/pipeline_task.py)
  — virou redundante (sempre é DB) (sre-devops P2).

**Gate:** `grep -rn "DiskArtifactStore" --include="*.py"` retorna 0.
Goldens verdes (sob `InMemoryArtifactStore`). Integration tests verdes
(sob `DBArtifactStore` em sqlite-memory).

**Canary obrigatório:** PR3 sobe atrás de canary 10% de workspaces por
72h antes de roll-out 100% (sre-devops P0), com gate em logs de erro
de `mathoms.pipeline` em staging + sanity check em workspace canário.

### PR4 — Drop schema + flag (~0.5 dia)

- Nova migration Alembic: `drop_workspace_use_db_artifacts_override`.
- Usar `op.batch_alter_table("workspaces")` para portabilidade
  Postgres ↔ SQLite (data-engineer P1; SQLite emula DROP COLUMN com
  rebuild — `batch_alter_table` cobre).
- **Guard pre-check no `upgrade()`** (data-engineer P0):
  ```python
  result = op.get_bind().execute(text(
      "SELECT count(*) FROM workspaces WHERE "
      "use_db_artifacts_override IS NOT NULL"
  )).scalar()
  if result > 0:
      raise RuntimeError(
          f"{result} workspace(s) com override setado — investigar antes de drop"
      )
  ```
- Migration reversível em estrutura (`downgrade` recria coluna
  `nullable=True`), **não reversível em dados** — documentar no
  docstring da revision.
- Remover campo `USE_DB_ARTIFACTS` de
  [backend/app/core/config.py:89](../../backend/app/core/config.py).
- Remover `use_db_artifacts_override` de
  [backend/app/models/workspace.py:28](../../backend/app/models/workspace.py).
- Arquivar runbook `docs/reference/runbooks/cutover.md` em
  `docs/archive/cutover-2026-05-XX.md` (referência histórica).

**Gate:** `grep -rn "USE_DB_ARTIFACTS\|use_db_artifacts" --include="*.py"`
retorna 0. Migration up/down testadas via
`alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.

## Não-objetivos (escopo intencionalmente excluído)

1. **Deletar `pipeline/artifact_store.py` por completo.** O `ArtifactStore`
   protocol, `InMemoryArtifactStore` (fake testável) e `DBArtifactStore`
   (backend wrapper, em `backend/app/services/db_artifact_store.py`)
   permanecem — eles são a interface de domínio + adapters legítimos.
   Apenas a implementação `DiskArtifactStore` morre.

2. **Migrar `scripts/e0_audit.py` para endpoint.** Read-only, opera em
   filesystem do workspace (não em `pipeline_artifacts`), serve para
   detectar duplicatas + arquivos órfãos antes de qualquer pipeline
   rodar. Mantém valor como CLI.

3. **Endpoint HTTP `POST /admin/workspaces/{id}/reset`.** Service-layer
   `reset_workspace_from_stage` em `backend/app/services/internal_ops/`
   é criado em PR1, mas o endpoint HTTP fica para sprint posterior
   dependente de IA-1 (auth staff + audit log persistido em DB + IP
   allowlist via Traefik + role `staff_admin` + rate limit DB-backed
   + confirmation token + bloqueio em `ENVIRONMENT=production` sem
   flag explícita). Lane em [docs/plan/INTERNAL_ADMIN/_README.md](../plan/INTERNAL_ADMIN/_README.md).

4. **`prepare_pipeline_config_dir` (ADR-211 lane 3).** Esta ADR remove
   o bloqueio CLI; a deleção em si fica para ADR-211 ou ADR follow-up.
   Dependência: PR1 desta ADR mergeado.

5. **Multi-tenant blob store (S3/MinIO).** ADR-083 deixou em aberto;
   continua em aberto. `DBArtifactStore` (Postgres) resolve para
   escala atual; revisita quando `pipeline_artifacts` cruzar 10GB ou
   1M rows.

6. **Política de retenção de `pipeline_artifacts`.** Sem
   `DiskArtifactStore` como pressure valve, todo artefato vai pra
   Postgres `JSONB` (estimativa: 7.5MB/workspace/mês, 90GB/ano com 1k
   workspaces). **Fora de escopo desta ADR**, registrado como débito
   em [docs/plan/PLATFORM_REVIEW/_README.md](../plan/PLATFORM_REVIEW/_README.md)
   §retention. Triggers para reabrir: tabela passa de 10GB ou 1M rows.

7. **Índice `pipeline_artifacts` com `created_at`.** `read_latest_artifact`
   faz seq scan sem composto incluindo timestamp (data-engineer P2).
   SRE follow-up; não bloqueia ADR-212.

## Nova estratégia de rollback (substitui ADR-118 §Rollback)

ADR-118 documentou rollback como "setar `MATHOMS_USE_DB_ARTIFACTS=false`
+ redeploy". Após PR4, essa opção morre. Nova estratégia, formalizada
em [docs/reference/runbooks/pipeline_rollback.md](../reference/runbooks/pipeline_rollback.md)
(PR1.5):

1. **Snapshot DB pré-deploy** — `pg_dump` das tabelas relevantes antes
   de cada deploy que toca pipeline (gate obrigatório, não prática
   informal).
2. **Revert PR via Git** — `gh pr revert <N>` cria PR de reverso; merge
   em `main`; auto-deploy. `git revert` cobre cleanup de código.
3. **Migration downgrade** se PR4 já tiver subido —
   `alembic downgrade -1` recria coluna `use_db_artifacts_override`
   (estrutura; dados perdidos, conforme docstring).
4. **Restore de snapshot** se houver corrupção de
   `pipeline_artifacts` — substituição por workspace (não tabela
   inteira; minimiza blast radius).

**Janela de recuperação:** ~30min (vs ~5min do flip-flag). Diferença
aceita porque:
- Flip-flag nunca foi exercitado em produção (1 ano+ desde ADR-118).
- Sua confiabilidade em incidente real era hipotética.
- Decision tree explícita no runbook reduz tempo de diagnóstico
  (compensa parte da diferença).
- Modo de falha mais previsível: code revert + DB restore é operação
  conhecida; flip-flag com cache stale, state intermediário, ou
  workspace pinned override era zona cinzenta.

**Cenário em que flip-flag teria sido salvador, revert não:** bug
latente em `DBArtifactStore` que corrompe artefatos sob workload
específico (ex.: race em upsert sob carga), detectado dia 1-2 após
PR3. Mitigação: **canary 10% por 72h** antes de roll-out 100% (gate
explícito de PR3); janela de revert real fica em dia 1-2, não dia 14.

## Consequências

**Positivas:**

- ✅ ~500 linhas deletadas líquido (~150 de `DiskArtifactStore` + ~150
  de branches + ~80 de flag/override resolver + ~120 de
  `e_reset.py` consolidado em service-layer).
- ✅ Caminho único de execução de pipeline — `DBArtifactStore` via
  Celery worker. Branches mortos somem de 30+ arquivos.
- ✅ `WorkspaceContext.__init__` exige `artifact_store` explícito —
  invariante por tipo, não por exceção runtime; SOLID DI.
- ✅ Validação JSON-schema vira hook universal pós-write em
  `DBArtifactStore` — protege todos os artefatos, não só os
  produzidos por `extract_with_llm`.
- ✅ Desbloqueia ADR-211 lane 3 (deletar `prepare_pipeline_config_dir`)
  e parcialmente ADR-120 (fallback de disco no reader morre).
- ✅ Backend é a única interface — alinha com posicionamento "pipeline
  como serviço" (ADR-112).
- ✅ Reduz superfície de teste — paridade disk-vs-db
  (`dev/compare_disk_vs_db.py`) e goldens de paridade morrem;
  `InMemoryArtifactStore` em goldens é ~100x mais rápido que
  alternativas.

**Negativas:**

- ⚠️ Workflow "editar JSON à mão e re-rodar stage seguinte" deixa de
  existir. Substituto: service-layer `reset_workspace_from_stage` +
  `POST /pipeline/run` com `from_stage=<name>`.
- ⚠️ Debug local de stage individual perde o atalho
  `python scripts/e3_reconcile.py`. Substituto: `make dev` + `POST
  /pipeline/run`. Custo cognitivo de subir backend para debug é real,
  mas o equivalente (Celery + DBArtifactStore + log estruturado) está
  mais perto da produção.
- ⚠️ Rollback de flip-flag deixa de existir. Substituto: snapshot DB
  pré-deploy + revert PR + migration downgrade. Aceito como trade-off
  (flip-flag nunca foi exercitado em produção; canary 10%/72h mitiga
  janela maior de revert).
- ⚠️ Endpoint HTTP de reset destrutivo fica pendente de IA-1 — janela
  pré-IA-1, ops opera via console interno local-only ou Python shell
  em emergência.
- ⚠️ **Débito explícito: política de retenção em `pipeline_artifacts`.**
  Sem `DiskArtifactStore`, crescimento é monotonic; estimativa 90GB/ano
  com 1k workspaces. Rastreado em [docs/plan/PLATFORM_REVIEW/_README.md](../plan/PLATFORM_REVIEW/_README.md);
  ADR follow-up dispara em 10GB ou 1M rows.

**Riscos identificados:**

| Risco | Prioridade | Mitigação |
|---|---|---|
| Pipeline em produção fica sem rollback rápido | P0 | Snapshot DB pré-deploy + revert PR + canary 10%/72h. Janela 30min vs 5min é aceitável dado risco-baseline pós-1-ano de DB-only |
| Bug em `DBArtifactStore` deixa de ter escape hatch | P0 | Goldens DB-only em `tests/test_e{3,4,5}_golden_execution.py` permanecem (sob `InMemoryArtifactStore`); +integration test multi-worker (ADR-111); canary obrigatório |
| Goldens E3/E4/E5 quebram em CI no momento do PR3 | P0 | Refactor de fixtures incluído no escopo do PR3 — injeta `InMemoryArtifactStore` via construtor explícito de `WorkspaceContext` |
| Migration não-portável SQLite (Alembic emula DROP COLUMN com rebuild) | P1 | `op.batch_alter_table("workspaces")` no `upgrade()`/`downgrade()` |
| Workspaces piloto com `use_db_artifacts_override=TRUE` legados | P0 | Guard `SELECT count(*) > 0 → raise` no `upgrade()` da migration PR4 (não só verbalizado em risco, enforçado em código) |
| Stages em CI rodando isoladamente (sem backend) | P1 | `InMemoryArtifactStore` em goldens; integration tests usam `DBArtifactStore` sqlite-memory |
| Validação JSON-schema perdida em `extract_with_llm.py` | P0 | Hook pós-write em `DBArtifactStore.write` (decisão explícita, não vago) — protege todos os stages, não só E1-LLM |
| Crescimento monotonic de `pipeline_artifacts` sem TTL | P2 | Nota de débito + ADR follow-up dispara em 10GB ou 1M rows |
| Premissa "Postgres-only em prod" implícita até hoje | P1 | Declarada explícita em §Decisão; gate para qualquer self-hosted futuro |

## Open questions — resolvidas

**OQ1: `scripts/e_reset.py` é deletado ou virou endpoint?**

**Resolvido (senior-cto + sre-devops convergem): delete puro + extract
service-layer.** Razões:
- Console interno (ADR-116) está em IA-0 local-only — depender de
  endpoint HTTP pré-IA-1 = risco de bloqueio + hardening insuficiente
  (sem auth staff, sem audit persistido).
- Reset destrutivo via HTTP exige auth + RBAC + audit + UX
  confirmação — não é "0.5 dia adicional", é 2-3 dias mínimo.
- Durante a janela sem endpoint, ops faz reset via service-layer
  diretamente (console interno local-only ou Python shell em
  emergência) — operação rara, custo aceitável.
- Endpoint vira lane separada em [docs/plan/INTERNAL_ADMIN/_README.md](../plan/INTERNAL_ADMIN/_README.md)
  pós-IA-1.

**OQ2: `scripts/e0_audit.py` permanece?**

**Resolvido: sim, fica como CLI.** Read-only sobre filesystem (não
toca `pipeline_artifacts`); custo zero; valor real para dev local.
Sem objeção em revisão.

**OQ3: PRs 1-4 numa sprint ou espalhados?**

**Resolvido: espalhados em 2 sprints com sub-ordem revisada.**
- **Sprint N**: PR2 → PR1 → PR1.5. Aguardar 1 semana em staging (não
  2 — flag nunca foi exercitada em 1 ano, soak adicional é cargo
  cult).
- **Sprint N+1**: PR3 (com canary 10%/72h obrigatório) → PR4.
- Total: ~5 dias úteis em ~3 semanas de calendário.

## Supersedure parcial: ADR-083 §Contexto

ADR-083 §Contexto bullet 1 ("Funcione tanto em CLI dev (disco, sem
DB) quanto em web (DB)") **fica obsoleta** com ADR-212. O resto da
ADR-083 (ArtifactStore protocol, InMemoryArtifactStore, requisito de
boundary `pipeline/` ↔ DB) **permanece válido**. Não está em
`supersedes:` do frontmatter por isso — supersedure parcial é
documentada aqui no corpo.

## Referências

- [ADR-083](083-artifactstore-abstracao-de-io-para-artefatos.md) — `ArtifactStore` protocol (parcialmente superseded: bullet "CLI dev sem DB" fica obsoleto)
- [ADR-106](106-opt-in-db-artifacts-por-workspace.md) — opt-in por workspace (superseded)
- [ADR-111](111-stateless-rigoroso-padrao-e-gate-empirico-a6f6.md) — stateless rigoroso (integration test multi-worker preserva gate empírico)
- [ADR-116](116-f7f-local-stack-next-separada-anonimizacao.md) — console interno (consumer do `internal_ops/pipeline_reset.py`)
- [ADR-118](118-flip-do-default-mathoms-use-db-artifacts-para-true.md) — flip default `True` (superseded)
- [ADR-120](120-readers-user-facing-consultam-artifactstore-db.md) — readers DB-first com fallback disco (parcialmente superseded; fallback morre)
- [ADR-211](211-llm-config-db-overrides.md) — cutover llm_config (esta ADR desbloqueia lane 3)
- [docs/reference/runbooks/cutover.md](../archive/cutover-2026-05-14.md) — runbook ADR-118 (será arquivado em PR4)
- [docs/reference/runbooks/pipeline_rollback.md](../reference/runbooks/pipeline_rollback.md) — runbook novo (criado em PR1.5)
