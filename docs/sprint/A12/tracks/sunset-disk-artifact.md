---
id: TRACK-sunset-disk-artifact
type: track
title: "Track Sunset DiskArtifactStore — 5 PRs sequenciais (ADR-212)"
sprint: A12
lane: "[[A12.sunset-disk-artifact]]"
status: ready
created_at: "2026-05-14"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a12
  - status/ready
  - area/backend
  - area/pipeline
  - area/ops
---

# Track Sunset DiskArtifactStore + flag + CLI standalone

> **Lane:** [[A12.sunset-disk-artifact]] · **ADR canônica:** [[ADR-212]]
> · **Branch prefix:** `agent/sunset-disk-artifact-pr<N>/*` (1 branch
> por PR; cada PR independentemente revertível)
> · **Pré-requisitos:** nenhum interno. [[ADR-211]] já mergeada em main.
> · **Supervisão obrigatória:** **senior-cto** (refactor de
> `WorkspaceContext`); **data-engineer** revisa PR3 (hook JSON-schema +
> goldens fixtures) e PR4 (Alembic guard + `batch_alter_table`);
> **sre-devops** revisa PR1.5 (runbook) e PR3 (gate canary).

## Briefing (1 frase)

Executar os 5 PRs sequenciais de [[ADR-212]] — deletar caminho
`DiskArtifactStore`, flag `MATHOMS_USE_DB_ARTIFACTS`, coluna
`use_db_artifacts_override` e CLI standalone do pipeline — mantendo
caminho único `DBArtifactStore` via Celery worker como execução
canônica.

## Por que ler [[ADR-212]] antes de codar

ADR-212 é o plano: §Decisão lista cada PR com arquivos exatos e linha,
§Não-objetivos delimita o escopo (não criar endpoint reset HTTP, não
deletar `e0_audit`, não mexer em retenção), §Riscos lista mitigações
enforçadas em código (não verbalizadas). **Não duplique conteúdo da
ADR neste track** — referencie seção.

## Ordem obrigatória dos PRs

1. **PR2 primeiro** (revisão senior-cto inverteu PR1↔PR2 — se algo quebra,
   sintoma aparece **antes** de deletar entrypoints CLI).
2. PR1 (deleta CLI + extrai service-layer).
3. PR1.5 (runbook — pré-requisito de PR3).
4. **Soak 1 semana** em staging — não 2 (cargo cult).
5. PR3 (deleta `DiskArtifactStore`) com **canary 10%/72h obrigatório**.
6. PR4 (drop coluna + flag).

## PR2 — Remover `MATHOMS_WORKSPACE_ROOT` setdefault (~0.5d)

**Arquivos:**
- `backend/app/main.py:8` — remover `os.environ.setdefault("MATHOMS_WORKSPACE_ROOT", ...)`.
- `backend/app/worker.py:25` — idem.
- `backend/app/tasks/pipeline_task.py:500` — remover `os.environ["MATHOMS_WORKSPACE_ROOT"] = ...`.
- `conftest.py` — **manter** (teste).

**Validação:**

```bash
make dev   # sobe limpo
grep -rn "MATHOMS_WORKSPACE_ROOT" backend/   # = 0
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
```

**Commit:** `refactor(backend): remove MATHOMS_WORKSPACE_ROOT setdefault (ADR-212 PR2)`

## PR1 — Deletar CLI standalone + extrair service-layer (~1d)

**Deletar `__main__` + `main()` de:**
- `scripts/e0_route.py`
- `scripts/e0_unlock.py`
- `scripts/e2_extract.py`

(Módulos continuam como libraries — importados por `pipeline/stages/*.py`.)

**Deletar `scripts/e_reset.py` (1406 linhas)**, mas **antes** extrair função:

```python
# backend/app/services/internal_ops/pipeline_reset.py
def reset_workspace_from_stage(
    db: Session,
    ws_id: UUID,
    from_stage: str,
    *,
    dry_run: bool = True,
    move_to_inbox: bool = False,
) -> ResetPreview:
    """Reseta artefatos de pipeline a partir de stage (consumido por console interno)."""
    ...
```

Teste unitário em `backend/tests/services/internal_ops/test_pipeline_reset.py`
sob `InMemoryArtifactStore` ([[ADR-083]] §Testabilidade).

**Manter:** `scripts/e0_audit.py` (read-only, inspeção FS).

**Docs:**
- `docs/reference/SETUP.md` §8 — substituir bloco CLI por "Pipeline roda
  exclusivamente via backend (Celery worker)."
- `docs/reference/SMOKE_TEST_HUMAN.md:209` — trocar
  `python scripts/e_reset.py --from E3 --dry-run` por chamada direta a
  `reset_workspace_from_stage` via console interno.

**Validação:**

```bash
grep -rn "if __name__" scripts/   # só e0_audit.py
pytest backend/tests/services/internal_ops -q
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
```

**Commit:** `refactor(pipeline): delete CLI standalone + extract reset service-layer (ADR-212 PR1)`

## PR1.5 — Runbook `pipeline_rollback.md` (~0.5d)

**Pré-requisito de PR3** (sre-devops P0). Criar `docs/reference/runbooks/pipeline_rollback.md`
com:

1. **Detecção** — gatilhos (anomalia em `mathoms.pipeline`, ≥5% runs failed
   em 1h via query SQL ad-hoc sobre `pipeline_runs`, corrupção em
   `pipeline_artifacts.content_json`).
2. **Snapshot pré-deploy obrigatório** —

   ```bash
   pg_dump --table=pipeline_artifacts --table=workspaces \
           --table=pipeline_runs --table=pipeline_stage_logs > snap.sql
   ```

3. **Decision tree** — corrupção localizada (1 ws) → restore por
   workspace; regressão global → revert PR + restore full; bug
   determinístico → fix-forward.
4. **Validação pós-rollback** — smoke test em workspace canário, 30min
   observação.
5. **RTO/RPO** — 30min RTO (vs 5min do flip-flag morto), RPO ≤24h.

Procedure **exercitada em staging** antes de mergear (não só escrita).
Owner: sre-devops.

**Commit:** `docs(runbook): add pipeline_rollback runbook (ADR-212 PR1.5)`

## Soak 1 semana

Entre PR1.5 mergeado e PR3 aberto: 7d wall-clock em staging com PR2+PR1
ativos. Monitorar `mathoms.pipeline` logs estruturados. Sem alertas →
prossegue para PR3.

## PR3 — Deletar `DiskArtifactStore` + cleanup (~2-3d)

**Maior PR da lane.** Toca 30+ arquivos. Sub-passos:

1. **Deletar classe `DiskArtifactStore`** em `pipeline/artifact_store.py`
   (~150 linhas). **Manter** `ArtifactStore` protocol e
   `InMemoryArtifactStore`.
2. **`pipeline/context.py`** — `WorkspaceContext.__init__` aceita
   `artifact_store: ArtifactStore` como parâmetro **obrigatório**.
   Refatorar callers de `WorkspaceContext.for_tenant` que omitem store.
3. **Remover branches** `if isinstance(store, DiskArtifactStore):` em:
   - `scripts/e3_reconcile.py:1087,1179`
   - `scripts/e4_categorize.py:1081`
   - `scripts/e5_analyze.py:3051`
   - `pipeline/stages/extract_with_llm.py:261`

   Manter lado "DB"; deletar lado "disk".
4. **Hook JSON-schema pós-write** em `DBArtifactStore.write`:

   ```python
   SCHEMA_BY_STAGE = {
       "e15_consolidate": "config/schemas/e15_consolidated.schema.json",
       "extract": "config/schemas/e2_extract.schema.json",
       # ... 5 entradas (E1.5, E2, E4, E5, pipeline)
   }

   def write(self, stage, key, data, *, document_id=None):
       schema_file = SCHEMA_BY_STAGE.get(stage)
       if schema_file and settings.SCHEMA_VALIDATION_STRICT:
           validate_dict(data, schema_file)
       # ... persist
   ```

5. **Deletar fallback de disco** em
   `backend/app/services/artifact_reader.py::read_latest_artifact` —
   DB-only ([[ADR-120]] fallback morre; DB-first preservada).
6. **Deletar:**
   - `backend/app/scripts/backfill_artifacts_from_disk.py`
   - `dev/compare_disk_vs_db.py`
7. **Deletar `_resolve_use_db_artifacts`** + chamada em
   `backend/app/tasks/pipeline_task.py:394`. Celery sempre instancia
   `DBArtifactStore`.
8. **Refatorar goldens E3/E4/E5** (`tests/test_e{3,4,5}_golden_execution.py`)
   para injetar `InMemoryArtifactStore` via construtor explícito de
   `WorkspaceContext`. DB-real em sqlite-memory fica em
   `backend/tests/integration/`.
9. **Limpar log** `pipeline_start using DBArtifactStore for run_id=...`
   em `backend/app/tasks/pipeline_task.py:480` (redundante).

**Validação:**

```bash
grep -rn "DiskArtifactStore" --include="*.py"   # = 0
pytest tests/test_e3_golden_execution.py -q     # verde (InMemoryArtifactStore)
pytest tests/test_e4_golden_execution.py -q
pytest tests/test_e5_golden_execution.py -q
pytest backend/tests/integration/test_multi_worker_concurrency.py -q  # ADR-111
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
```

**Canary obrigatório:** PR3 sobe atrás de canary 10% de workspaces por
72h em staging antes de roll-out 100%. Gate: logs de erro `mathoms.pipeline`
+ sanity check em workspace canário.

**Commit:** `refactor(pipeline): delete DiskArtifactStore + DB-only execution path (ADR-212 PR3)`

## PR4 — Alembic drop + remove flag (~0.5d)

**Migration nova:** `backend/alembic/versions/<hash>_drop_workspace_use_db_artifacts_override.py`

```python
def upgrade() -> None:
    result = op.get_bind().execute(text(
        "SELECT count(*) FROM workspaces WHERE use_db_artifacts_override IS NOT NULL"
    )).scalar()
    if result > 0:
        raise RuntimeError(
            f"{result} workspace(s) com use_db_artifacts_override setado — "
            "investigar antes de drop"
        )
    with op.batch_alter_table("workspaces") as batch:
        batch.drop_column("use_db_artifacts_override")

def downgrade() -> None:
    """Reversível em estrutura; NÃO reversível em dados (overrides perdidos)."""
    with op.batch_alter_table("workspaces") as batch:
        batch.add_column(sa.Column("use_db_artifacts_override", sa.Boolean(), nullable=True))
```

**Remover:**
- `backend/app/core/config.py:89` — campo `USE_DB_ARTIFACTS`.
- `backend/app/models/workspace.py:28` — atributo `use_db_artifacts_override`.

**Arquivar:**
- `git mv docs/reference/runbooks/cutover.md docs/archive/cutover-YYYY-MM-DD.md`
- Entrada em `docs/archive/README.md` (≤8 linhas).

**Flippar [[ADR-212]]:** `Proposto` → `Decidido (A12.sunset-disk-artifact)`
no frontmatter.

**Validação:**

```bash
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
grep -rn "USE_DB_ARTIFACTS\|use_db_artifacts" --include="*.py"   # = 0
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
```

**Commit:** `refactor(db): drop workspaces.use_db_artifacts_override + USE_DB_ARTIFACTS settings (ADR-212 PR4)`

## Decisões já tomadas ([[ADR-212]] §Open questions)

- **OQ1:** `e_reset.py` → delete + extract service-layer (não endpoint HTTP).
- **OQ2:** `e0_audit.py` permanece como CLI.
- **OQ3:** PR2+PR1+PR1.5 → soak 1 semana → PR3 (com canary) + PR4. ~3 semanas calendário, ~5d eng.

## Ligações

- ADR canônica: [[ADR-212]] (Proposto)
- Lane: [[A12.sunset-disk-artifact]]
- Pré-req externo: nenhum
- Desbloqueia: [[ADR-211]] lane 3 (`prepare_pipeline_config_dir`)
- Relacionado: [[ADR-083]] (parcialmente superseded), [[ADR-118]] (superseded), [[ADR-106]] (superseded), [[ADR-120]] (parcialmente superseded), [[ADR-111]] (stateless rigoroso — gate empírico preservado), [[ADR-116]] (console interno — consumer)
