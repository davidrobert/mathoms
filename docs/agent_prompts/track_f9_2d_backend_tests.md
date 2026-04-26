# Track F9.2d — Strings descritivas em `backend/app/` residual + tests não-golden

> **Lane ID:** F9.2d
> **Branch prefix:** `agent/f9-stage-rename/2d-backend-tests/*`
> **Depende de:** F9.2a ✅ (pipeline core), idealmente F9.2b ✅ (scripts) para tests de scripts
> **Bloqueia:** F9.2e (closeout)
> **Paralelo com:** F9.2b, F9.2c (escopos disjuntos)
> **Onda:** F9 (sub-fatia 3d/7)
> **Fonte de verdade:** [ADR-093](../DECISIONS.md#adr-093) · [`STAGE_RENAME_MAP`](../../pipeline/stage_spec.py#L54)

> **Objetivo:** flipar strings legadas restantes em `backend/app/` (residual)
> e em testes não-golden em `tests/` e `backend/tests/`. Goldens permanecem
> intocados — só atualize se o produtor passou a emitir descritivo
> (regeneração documentada no commit).

---

## Estado atual

T1 já flipou serviços principais (`pipeline_service.py`, `artifact_repository.py`).
Resíduo backend é pequeno (~40 hits). Tests têm bastante volume (~600 hits)
mas a maioria é literal `"E3"` em fixtures/asserts que pode ir via grep + edit
direcionado.

## Hotspots backend (≈40 hits)

```
11  backend/app/scripts/backfill_artifacts_from_disk.py
 3  backend/app/services/document_extract_json_service.py
 3  backend/app/repositories/pipeline_artifact_repository.py
 2  backend/app/services/document_pipeline_sync.py
 2  backend/app/services/transaction_service.py
 2  backend/app/models/pipeline_artifact.py
 1  backend/app/services/dashboard_service.py
 1  backend/app/services/document_processor.py
 1  backend/app/services/retry_config.py
 1  backend/app/tasks/pipeline_task.py
 1  backend/app/schemas/pipeline.py
```

## Hotspots tests (≈600 hits — não-golden filter abaixo)

```
72  tests/unit/pipeline/test_artifact_stores.py
49  backend/tests/test_db_artifact_store.py
35  tests/unit/pipeline/test_e3_reconciler_adapter.py
26  backend/tests/test_events.py
21  backend/tests/test_pipeline_stage_log_repository.py
17  tests/unit/pipeline/test_e5_analyzer_adapter.py
16  backend/tests/test_pipeline_artifact_repository.py
15  tests/test_orchestrator.py
13  backend/tests/test_stage_duration_estimator.py
12  backend/tests/fixtures/pipeline_runs.py
11  tests/unit/pipeline/test_e4_categorizer_adapter.py
10  backend/tests/test_pipeline_client.py
 9  tests/test_live_progress.py
 8  backend/tests/test_pipeline_task.py
 8  backend/tests/test_pipeline_phase5.py
 8  backend/tests/test_backfill_artifacts_from_disk.py
 7  tests/unit/pipeline/test_e2_caminho_b.py
 7  tests/test_llm_stages_per_stage.py
 7  backend/tests/test_otel_traces.py
 7  backend/tests/test_artifact_reader.py
 6  tests/unit/pipeline/test_e4_serialization.py
 6  tests/test_pipeline_context.py
+ vários menores
```

**NÃO mexer (goldens):**
- `tests/pipeline/goldens/**`
- `tests/fixtures/pipeline_golden/**`
- `tests/test_e3_golden_execution.py`, `test_e4_golden_execution.py`,
  `test_e5_golden_execution.py`, `test_e5n_golden_execution.py`,
  `test_llm_golden.py`
- `tests/pipeline/perf/baseline_disk.json` (baseline de performance, não stage-aware)

Se algum desses tests **falhar** porque o produtor agora emite descritivo,
**regenere o golden** com nota explícita no commit (ex.: `test(goldens):
regenera e3 cenarios para emitir reconcile_transactions (F9.2d)`).

## Estratégia

### Tier A — Backend residual (commit)

Substituir literais nos 11 arquivos listados acima.
- `backfill_artifacts_from_disk.py` — script CLI; usar `resolve_stage_name`
  no input + descritivo nas chamadas internas.
- `pipeline_artifact_repository.py` — atenção: queries DB ainda recebem rows
  legadas até F9.3. Use `resolve_stage_name` em INPUT, mas continue gravando
  legacy via `to_legacy_stage_name` se necessário (ou deixe a row passar — DB
  é F9.3). Documente decisão no commit.
- `models/pipeline_artifact.py` — pode ser docstring; verifique.
- `schemas/pipeline.py` — Literal[stage]? Se sim, T3 (OpenAPI snapshot já foi
  regenerado em main, então atualize o Literal e rode `make
  update-openapi-snapshot` se mudar — provavelmente não é necessário).

**Gate:** `pytest backend/tests -q` verde.
**Commit:** `refactor(backend): residual stage strings descritivas (F9.2d — Tier A)`

### Tier B — Tests pipeline (commit)

Files em `tests/`:
- `tests/unit/pipeline/test_artifact_stores.py` (72)
- `tests/unit/pipeline/test_e3_reconciler_adapter.py` (35)
- `tests/unit/pipeline/test_e5_analyzer_adapter.py` (17)
- `tests/unit/pipeline/test_e4_categorizer_adapter.py` (11)
- `tests/test_orchestrator.py` (15)
- `tests/unit/pipeline/test_e2_caminho_b.py` (7)
- `tests/test_llm_stages_per_stage.py` (7)
- `tests/unit/pipeline/test_e4_serialization.py` (6)
- `tests/test_pipeline_context.py` (6)
- `tests/test_live_progress.py` (9)
- `tests/test_llm_stages.py` (resíduo se houver)
- `tests/test_stage_wrappers.py` (5)
- `tests/test_run_dev_smoke.py` (2)
- `tests/test_e3_dedup.py` (1)
- `tests/test_schema_validation.py` (3)
- `tests/test_regression.py` (4)
- `tests/unit/pipeline/test_baseline_normalizer.py` (4)
- `tests/unit/pipeline/test_e5_serialization.py` (1)
- `tests/unit/pipeline/test_investments_consolidator.py` (1)
- `tests/unit/pipeline/test_patrimonio_resolvers.py` (1)

**Gate:** `pytest tests -q` verde.
**Commit:** `test(pipeline): stage strings descritivas em tests não-golden (F9.2d — Tier B)`

### Tier C — Tests backend (commit)

Files em `backend/tests/`:
- `test_db_artifact_store.py` (49)
- `test_events.py` (26)
- `test_pipeline_stage_log_repository.py` (21)
- `test_pipeline_artifact_repository.py` (16)
- `test_stage_duration_estimator.py` (13)
- `fixtures/pipeline_runs.py` (12)
- `test_pipeline_client.py` (10)
- `test_pipeline_task.py` (8)
- `test_pipeline_phase5.py` (8)
- `test_backfill_artifacts_from_disk.py` (8)
- `test_otel_traces.py` (7)
- `test_artifact_reader.py` (7)
- `regressions/test_anti_regression_bank.py` (resíduo)

**Atenção:** alguns testes podem comparar diretamente strings legadas com
rows DB que ainda são legadas. Esses asserts ficam **sob a janela F9.2 → F9.3**.
Decisão por arquivo: se o teste lê DB e compara contra row, mantenha legacy
no assert + comentário `# DB rows ainda legadas; F9.3 endereça`. Se o teste
manipula apenas in-memory ou through service layer, flip completo.

**Gate:** `pytest backend/tests -q` verde.
**Commit:** `test(backend): stage strings descritivas em tests não-golden (F9.2d — Tier C)`

---

## Sequência

```bash
git fetch origin
git checkout -b agent/f9-stage-rename/2d-backend-tests/$(date +%Y%m%d-%H%M)
source ../../../.venv/bin/activate

pytest tests -q 2>&1 | tail -3
pytest backend/tests -q 2>&1 | tail -3

# Tier A → B → C (pytest entre)

pre-commit run --all-files
pytest tests -q
pytest backend/tests -q

git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q
git push origin HEAD:main
```

## Critérios de aceite

- [ ] `grep -rn '"E[0-9]' backend/app/` retorna apenas: STAGE_RENAME_MAP refs,
  comentários explicitando legacy, ou rows DB intencionais até F9.3.
- [ ] Tests não-golden flipados; goldens intocados (ou regenerados com nota).
- [ ] `pytest tests -q` (1458+) e `pytest backend/tests -q` (1307+) verdes.
- [ ] `pre-commit run --all-files` verde.

## Anti-padrões

- ❌ Editar goldens diretamente (regenere via produtor + nota no commit).
- ❌ Comparar com row DB legacy via assert sem comentar a janela F9.2→F9.3.
- ❌ Misturar Tier A/B/C em commit único — separar para reviewabilidade.

## Referências

- [F9.2a pipeline core](track_f9_2a_pipeline_core_strings.md)
- [F9.2b scripts](track_f9_2b_scripts_strings.md)
- [F9.2 master](track_f9_2_string_literals.md)
- [F9.3 alembic](track_f9_3_alembic_migration.md) — fecha janela DB legacy
- [F9.2e closeout](track_f9_2e_closeout.md)
