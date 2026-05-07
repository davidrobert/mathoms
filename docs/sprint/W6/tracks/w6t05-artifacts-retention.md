---
id: TRACK-w6t05-artifacts-retention
type: track
title: "Track W6-T05 — Pipeline artifacts retention + cascade-on-delete"
sprint: W6
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/w6
  - status/consumed
---

# Track W6-T05 — Pipeline artifacts retention + cascade-on-delete

> **Lane ID:** `w6t05-artifacts-retention`
> **Branch prefix:** `agent/w6t05-artifacts-retention/<NN>/<yyyyMMdd-HHmm>`
> **Plano canônico:** [plan/PLATFORM_REVIEW/_README.md §W6-T05](../plan/PLATFORM_REVIEW/_README.md)
> **Onda:** Wave 6 (paraleliza com Wave 5)
> **Severity:** P2 · **Effort:** M (5 PRs sequenciais)
> **Owner:** data-engineer
> **Depende de:** —
> **Findings cobertos:** DE-010, DE-011, DE-017, DE-022
> **ADR sugerida:** ADR-Proposto antes do PR-1 (FK + retention é arquitetural mesmo P2)

> **Objetivo (1 frase):** dar a `pipeline_artifacts` lifecycle gerenciado
> (retention TTL + prune diário) e fechar gap de cascade no delete
> singular de Document.

---

## Por que esta lane

### Estado atual auditado

**Schema** (`backend/app/models/pipeline_artifact.py` + migration `p4q5r6s7t8u9_pipeline_artifacts.py`):

- Colunas: `id`, `workspace_id`, `pipeline_run_id`, `stage`, `artifact_key`, `document_id`, `content_json`, `schema_version` (já **existe** mas nullable e nunca populada — DE-022), `byte_size`, `created_at`.
- **Não tem `retention_until`.** Artefatos persistem indefinidamente.
- FKs:
  - `workspace_id → workspaces.id ON DELETE CASCADE` ✓
  - `pipeline_run_id → pipeline_runs.id ON DELETE CASCADE` ✓
  - `document_id → documents.id ON DELETE SET NULL` ⚠️ (órfãos com PII ficam para sempre)
- Índices: `workspace_id`, `pipeline_run_id`, `(workspace_id, stage, artifact_key)`, `document_id`.
- Unique: `(pipeline_run_id, stage, artifact_key)`.

**Cascade no delete singular** (`backend/app/services/internal_ops/delete_document.py`):

`await db.delete(doc)` apenas remove a linha. Por causa do `ON DELETE SET NULL`, artefatos E2 ligados sobrevivem com `document_id=NULL` — órfãos contendo PII permanecem. `purge_documents` cascata via `pipeline_runs` (test existe). Caminho singular não.

**Sem prune** (`backend/app/tasks/periodic_tasks.py`): beat schedule já tem `lgpd-expire-data-exports` e `lgpd-process-user-deletions` — adicionar `prune-pipeline-artifacts` segue mesmo padrão.

### Por que importa

- **DE-017:** sem retention, `pipeline_artifacts` cresce monotonicamente. Postgres `JSONB` row de E5 ~50-200KB × N runs × workspaces = explosão silenciosa.
- **DE-010:** PII em E2/E5 sobrevive ao delete do Document. W2-T01 (Fernet) cobre "vaza em backup" mas não fecha "data minimization" LGPD Art. 16, II.
- **DE-022:** `schema_version` existe na coluna mas nunca é gravada — quando W6-T01 bumpar schemas E4/E5, sem como filtrar reads por versão.
- **DE-011:** sem cascade explícita, lineage doc → artefato fica inconsistente.

---

## Regras inegociáveis

1. **Migration online**: `ADD COLUMN ... NULL` + backfill em batch separado + (se aplicável) `SET NOT NULL` em segunda migration. `pipeline_artifacts` é hot.
2. **FK alteration via `batch_alter_table`** com `lock_timeout`. Trocar `ON DELETE SET NULL` → `CASCADE` em FK existente em Postgres exige `DROP CONSTRAINT` + `ADD CONSTRAINT`.
3. **Backfill é stage separado** (`backend/alembic/data_migrations/backfill_artifact_retention.py`).
4. **`schema_version` nullable continua** (já é). Default `'v1'` em writes via store, não no schema.
5. **Workspace-scoped sem expiração** (`db_artifact_store._WORKSPACE_SCOPED_STAGES`): `extract_members`, `extract_baseline`, `consolidate_baseline`, `extract_irpf_full` (+ legacy) — `retention_until=NULL`. Stages run-scoped (E2/E3/E4/E5) → 90d default.
6. **Determinismo de prune**: `WHERE retention_until IS NOT NULL AND retention_until < NOW()`.
7. **Reversibilidade**: downgrade restaura `SET NULL` e dropa `retention_until`.

---

## Entregáveis

### Migration 1 — estrutura (`<rev>_artifact_retention_schema.py`)

```sql
ALTER TABLE pipeline_artifacts
  ADD COLUMN retention_until TIMESTAMPTZ NULL;

CREATE INDEX CONCURRENTLY ix_pipeline_artifacts_retention_until
  ON pipeline_artifacts (retention_until)
  WHERE retention_until IS NOT NULL;

ALTER TABLE pipeline_artifacts
  DROP CONSTRAINT pipeline_artifacts_document_id_fkey,
  ADD CONSTRAINT pipeline_artifacts_document_id_fkey
    FOREIGN KEY (document_id)
    REFERENCES documents(id)
    ON DELETE CASCADE;
```

Em SQLite (testes): `op.batch_alter_table` recria com a nova FK.

### Data migration 2 — backfill `schema_version` (`<rev>_backfill_artifact_schema_version.py`)

```sql
UPDATE pipeline_artifacts SET schema_version = 'v1' WHERE schema_version IS NULL;
-- batched 10000/loop, atomic per batch
```

`retention_until` **não** é backfilled — artefatos legados ficam NULL
(nunca expiram). Política aplicada apenas a writes novos.

### Domain — `backend/app/services/artifact_retention_policy.py`

```python
WORKSPACE_SCOPED_STAGES = frozenset({...})  # mesmo set de db_artifact_store._WORKSPACE_SCOPED_STAGES
RUN_SCOPED_DEFAULT_DAYS = 90

def compute_retention_until(stage: str, *, now: datetime) -> datetime | None:
    if stage in WORKSPACE_SCOPED_STAGES:
        return None
    return now + timedelta(days=RUN_SCOPED_DEFAULT_DAYS)
```

**Decisão:** quem é dono do scope? **Não criar coluna `scope`.**
`_WORKSPACE_SCOPED_STAGES` é a fonte de verdade hoje (ADR-132/157) —
duplicar em coluna abre drift. Mover o set para
`artifact_retention_policy.py` e re-exportar de `db_artifact_store`.

**Override por config:** `pipeline.json → artifact_retention.run_scoped_days: 90`. Workspace-level override **não** introduzido nesta lane (YAGNI).

### Store — write path

`backend/app/services/db_artifact_store.py::write` chama
`compute_retention_until(stage, now=...)` e popula `retention_until` +
`schema_version='v1'` em INSERTs. UPDATE preserva `retention_until`
existente (rerun não estende vida).

### Prune task — `backend/app/tasks/prune_artifacts.py`

```python
@celery_app.task(name="fin.prune_pipeline_artifacts", bind=True, max_retries=1)
def prune_pipeline_artifacts(self) -> dict[str, int]:
    """Delete artefatos com retention_until < now. Loop em batches de 1000."""
```

Beat schedule em `backend/app/worker.py`:

```python
"prune-pipeline-artifacts-daily": {
    "task": "fin.prune_pipeline_artifacts",
    "schedule": 86400.0,
},
```

### Cascade no delete singular

`backend/app/services/internal_ops/delete_document.py` — após FK virar
`CASCADE`, `await db.delete(doc)` cascata sozinho. **Validar com
test**, não confiar.

Test novo `backend/tests/internal_ops/test_delete_document_cascades_artifacts.py`:
- Setup: doc + artefato E2 com `document_id`.
- `delete_document(...)`.
- Assert: artefato sumiu (não ficou com `document_id=NULL`).

---

## Sequência de PRs (CRÍTICO — ordem importa)

```
PR-1: feat(db): pipeline_artifacts retention_until + cascade FK + index (W6-T05 · ADR-NNN Proposto)
PR-2: chore(db): backfill schema_version='v1' em rows legadas (W6-T05)
PR-3: feat(pipeline): artifact_retention_policy + write path popula retention_until/schema_version (W6-T05)
PR-4: feat(tasks): prune_pipeline_artifacts daily celery beat (W6-T05)
PR-5: test(internal_ops): delete_document cascades artifacts (W6-T05)
PR-6: docs(adrs): ADR-NNN Decidido + CHANGELOG + DB_SCHEMA_REFERENCE refresh (W6-T05)
```

**Não fundir PRs.** PR-3 sem PR-1 quebra (coluna não existe). PR-4 sem
PR-3 é no-op (rows sem retention_until populada).

---

## Risco de breakage em workspaces existentes

| Risco | Vetor | Mitigação |
|---|---|---|
| **Crescimento de `pipeline_artifacts` em prod hoje** | Migration PR-1 só adiciona coluna nullable — zero impacto em runs ativas. | Online ADD COLUMN + CREATE INDEX CONCURRENTLY. |
| **FK swap durante runs ativas** | `DROP CONSTRAINT` em Postgres pega `ACCESS EXCLUSIVE` momentâneo. | Janela de manutenção fora horário de pipeline. `lock_timeout=5s` + retry. |
| **Rows legadas com `retention_until=NULL`** | Pruner ignora — comportamento intencional. | Documentar em ADR. Backfill manual via `dev/backfill_artifact_retention.py` se ops quiser limpar. |
| **Cascade deleta artefato que outra run referencia** | Improvável: `document_id` aponta para o doc-fonte de E2 only. E3/E4/E5 não têm `document_id`. | Test exhaustivo do cascade. |
| **SQLite em testes não suporta `CREATE INDEX CONCURRENTLY`** | Migration falha em CI. | `op.create_index(... postgresql_concurrently=True, postgresql_where=...)` + dialect-aware fallback. |
| **PII em rows com `retention_until=NULL` pré-PR-3** | Cascade fecha "doc deletado", mas artefato sem doc associado fica indefinido. | W2-T01 (Fernet) é defesa em profundidade. Esta lane fecha o vetor "doc deletado". |

---

## Gates de push

```bash
pre-commit run --all-files
pytest backend/tests/test_pipeline_artifact_model.py -q
pytest backend/tests/test_pipeline_artifact_repository.py -q
pytest backend/tests/internal_ops/test_documents.py -q
pytest backend/tests/internal_ops/test_delete_document_cascades_artifacts.py -q  # novo
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
make smoke
```

---

## Acceptance gates

- [ ] Migration PR-1 mergeada com upgrade/downgrade testados em SQLite + Postgres staging.
- [ ] `schema_version='v1'` populada em todas as rows pós-PR-2.
- [ ] Store grava `retention_until` em writes novos (run-scoped) e NULL (workspace-scoped).
- [ ] `prune_pipeline_artifacts` task executa e delete-count > 0 em smoke staging.
- [ ] `delete_document` cascata para artefatos via test novo.
- [ ] `purge_documents` test continua verde (não regrediu).
- [ ] DB_SCHEMA_REFERENCE.md regenerado.
- [ ] ADR-NNN Decidido (rationale + alternativas).

---

## O que NÃO entrega

- Encryption de PII em `content_json` (W2-T01).
- Workspace-level override de retention dias (YAGNI).
- Backfill retroativo de `retention_until` em rows legadas (script opcional, não automatizado).
- Schema bumping em `pipeline.json` (W6-T01).

---

## Coordenação

- **Disjunto a W6-T01** (não toca FK ou retention).
- **Disjunto a W2-T01** (Fernet — toca `content_json` write path; coordenar order de patches no `db_artifact_store.write`).
- **Hotspot:** `backend/app/services/db_artifact_store.py` — Fernet (W2-T01) e retention (esta lane) ambos modificam `write`. Quem mergeia segundo rebase + retest.
