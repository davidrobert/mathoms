# Code Style Audit — 2026-04-21

Commit: `66016b2`  
Files scanned: 467 Python + 159 TypeScript  
Total offenders: 2047

## Sumário por categoria

| Categoria | Count | High+ |
|---|---|---|
| P1_long_functions | 810 | 281 |
| P2_long_files | 31 | 7 |
| P3_dict_str_any_boundary | 71 | 71 |
| P4_optional_no_default | 4 | 0 |
| P5_float_money | 79 | 79 |
| P6_forbidden_names | 2 | 0 |
| P7_multiparagraph_docstring | 706 | 0 |
| P8_what_comments | 58 | 0 |
| P9_deep_nesting | 233 | 0 |
| T1_ts_any | 9 | 9 |
| T2_ts_long_files | 7 | 2 |
| T3_ts_long_functions | 24 | 13 |
| T4_ts_forbidden_filename | 1 | 0 |
| T5_ts_hex_colors | 12 | 0 |

## Sumário por severidade

| Severidade | Count |
|---|---|
| critical | 0 |
| high | 462 |
| med | 556 |
| low | 1001 |
| info | 28 |

## Top ofensores (prioridade de sweep)

### P1_long_functions

- `scripts/e_reset.py:779` **high** · `main` · len=372
- `scripts/e6_render.py:3408` **high** · `build_sections` · len=331
- `scripts/e5n_narrativas.py:233` **high** · `load_metrics_from_e5` · len=297
- `pipeline/domain/services/narrativas/charts_narrator.py:29` **high** · `narrate` · len=284
- `backend/app/tasks/pipeline_task.py:356` **high** · `run_pipeline_task` · len=273
- `scripts/e6_render.py:934` **high** · `build_charts` · len=266
- `scripts/e6_render.py:1321` **high** · `build_tactical_dashboard` · len=228
- `scripts/e3_reconcile.py:1003` **high** · `main` · len=222
- `scripts/e7_review.py:194` **high** · `run_cross_validation` · len=216
- `scripts/e5_analyze.py:436` **high** · `_build_members_from_consolidated` · len=213

### P2_long_files

- `scripts/e6_render.py:1` **high** · `e6_render.py` · len=3875
- `scripts/e5_analyze.py:1` **high** · `e5_analyze.py` · len=2862
- `scripts/e3_reconcile.py:1` **high** · `e3_reconcile.py` · len=1478
- `scripts/e_reset.py:1` **high** · `e_reset.py` · len=1333
- `scripts/e4_categorize.py:1` **high** · `e4_categorize.py` · len=1268
- `scripts/e7_review.py:1` **high** · `e7_review.py` · len=1090
- `tests/fixtures/pdf_generator.py:1` **high** · `pdf_generator.py` · len=1067
- `scripts/e0_audit.py:1` **med** · `e0_audit.py` · len=949
- `scripts/e0_route.py:1` **med** · `e0_route.py` · len=939
- `tests/test_llm_stages.py:1` **med** · `test_llm_stages.py` · len=921

### P3_dict_str_any_boundary

- `backend/app/api/config.py:174` **high** · `_load_global_json.return` · len=1
- `backend/app/api/config.py:182` **high** · `_load_global_yaml.return` · len=1
- `backend/app/api/config.py:663` **high** · `_import_family_members.data` · len=1
- `backend/app/api/config.py:705` **high** · `_import_categorization.data` · len=1
- `backend/app/api/config.py:733` **high** · `_export_blob_or_default.return` · len=1
- `backend/app/api/config.py:756` **high** · `_export_family_members.return` · len=1
- `backend/app/api/config.py:812` **high** · `_export_categorization.return` · len=1
- `pipeline/domain/services/cenarios_conjuge_analyzer.py:176` **high** · `analyze.patrimonio` · len=1
- `pipeline/domain/services/cenarios_conjuge_analyzer.py:177` **high** · `analyze.goals` · len=1
- `pipeline/domain/services/cenarios_conjuge_analyzer.py:178` **high** · `analyze.fluxo` · len=1

### P4_optional_no_default

- `backend/app/schemas/pipeline.py:22` **low** · `validate_from_stage.v` · len=1
- `backend/app/scripts/backfill_artifacts_from_disk.py:55` **low** · `_iter_workspaces.workspace_id` · len=1
- `backend/app/services/audit.py:66` **low** · `_client_meta.request` · len=1
- `backend/app/services/task_progress_service.py:49` **low** · `_load_aporte_keywords_from_config.tenant_root` · len=1

### P5_float_money

- `backend/app/schemas/dto/config_blob/response.py:32` **high** · `saldo_diff` · len=1
- `backend/app/schemas/goal.py:24` **high** · `renda_passiva_mensal_brl` · len=1
- `backend/app/schemas/goal.py:60` **high** · `if_meta_brl` · len=1
- `backend/app/schemas/goal.py:64` **high** · `aporte_necessario_mensal_brl` · len=1
- `backend/app/schemas/goal.py:72` **high** · `if_meta_conservadora_brl` · len=1
- `backend/app/schemas/goal.py:179` **high** · `meta_aporte_mensal_brl` · len=1
- `backend/app/schemas/goal.py:208` **high** · `aporte_anual_brl` · len=1
- `backend/app/schemas/goal.py:250` **high** · `aporte_mensal_brl` · len=1
- `backend/app/schemas/transactions.py:12` **high** · `valor` · len=1
- `backend/app/schemas/transactions.py:24` **high** · `total_receitas` · len=1

### P6_forbidden_names

- `backend/tests/test_structured_logging.py:126` **med** · `handler` · len=1
- `backend/tests/test_structured_logging.py:144` **med** · `handler` · len=1

### P7_multiparagraph_docstring

- `tests/fixtures/pdf_generator.py:1` **low** · `<module>` · len=60
- `scripts/lint/check_workspace_scoping.py:1` **low** · `<module>` · len=59
- `backend/tests/test_multi_tenant_isolation.py:1` **low** · `<module>` · len=48
- `backend/tests/fixtures/pipeline_runs.py:1` **low** · `<module>` · len=43
- `backend/app/core/tenancy.py:1` **low** · `<module>` · len=39
- `dev/commit.py:1` **low** · `<module>` · len=37
- `backend/tests/conftest.py:1` **low** · `<module>` · len=36
- `backend/app/services/audit_service.py:1` **low** · `<module>` · len=35
- `backend/tests/fixtures/llm_mock.py:1` **low** · `<module>` · len=35
- `pipeline/domain/services/e5_analyzer_adapter.py:1` **low** · `<module>` · len=34

### P8_what_comments

- `backend/app/scripts/cutover_execute.py:120` **low** · `# Check pré-condições` · len=1
- `backend/app/tasks/pipeline_task.py:168` **low** · `# Check idempotência: se já existem suggestions desse run, p` · len=1
- `backend/tests/test_category_repository.py:132` **low** · `# update que mantém a chave atual).` · len=1
- `backend/tests/test_pipeline_api.py:129` **low** · `# Get run detail` · len=1
- `backend/tests/test_task_service.py:301` **low** · `# Update parcial` · len=1
- `scripts/e0_audit.py:153` **low** · `# Check 1: Filename vs JSON content mismatch` · len=1
- `scripts/e0_audit.py:237` **low** · `# Check 2: Orphan files (data/ ↔ E2_extracts/)` · len=1
- `scripts/e0_audit.py:290` **low** · `# Check 3: Possible duplicates in data/` · len=1
- `scripts/e0_audit.py:323` **low** · `# Check for exact duplicates (same period)` · len=1
- `scripts/e0_audit.py:334` **low** · `# Check for overlapping periods (one file contained inside a` · len=1

### P9_deep_nesting

- `tests/fixtures/pdf_generator.py:891` **low** · `generate_statement` · len=13
- `scripts/e4_categorize.py:589` **low** · `process_transactions` · len=12
- `dev/generate_db_schema_reference.py:98` **low** · `_sql_to_go` · len=9
- `scripts/e_reset.py:779` **low** · `main` · len=9
- `pipeline/llm/text_extractor.py:47` **low** · `extract` · len=7
- `scripts/e6_render.py:3408` **low** · `build_sections` · len=7
- `scripts/e_reset.py:715` **low** · `validate` · len=7
- `scripts/e0_route.py:270` **low** · `_extract_file_preview` · len=6
- `scripts/e15_consolidate.py:355` **low** · `consolidate_from_itens` · len=6
- `scripts/e2_extract.py:217` **low** · `run_with_store` · len=6

### T1_ts_any

- `frontend/src/app/(app)/dashboard/page.tsx:228` **high** · `? (entry: any) => {` · len=1
- `frontend/src/components/report/sections/S3InvestimentosSection.tsx:47` **high** · `<InvestimentosClasseCard investimentos={inv as any} />` · len=1
- `frontend/src/components/report/sections/S3InvestimentosSection.tsx:51` **high** · `estrategia={estrategiaAporte as any}` · len=1
- `frontend/src/components/report/sections/S3InvestimentosSection.tsx:58` **high** · `contrafluxo={inv?.contrafluxo as any}` · len=1
- `frontend/src/components/report/sections/S3InvestimentosSection.tsx:66` **high** · `{typeof (ratios as any).rentabilidade_pct === "number"` · len=1
- `frontend/src/components/report/sections/S3InvestimentosSection.tsx:67` **high** · `? `${((ratios as any).rentabilidade_pct as number).toFixed(2)}%`` · len=1
- `frontend/src/components/report/sections/S3InvestimentosSection.tsx:68` **high** · `: String((ratios as any).rentabilidade_pct ?? "N/D")}` · len=1
- `frontend/src/components/report/sections/S7IndependenciaSection.tsx:33` **high** · `<PrevidenciaPgblCard previdencia={previdencia as any} />` · len=1
- `frontend/src/lib/api.ts:497` **high** · `data: any;` · len=1

### T2_ts_long_files

- `frontend/src/lib/api.ts:1` **high** · `api.ts` · len=1880
- `frontend/src/app/(app)/pipeline/page.tsx:1` **high** · `page.tsx` · len=1195
- `frontend/src/app/(app)/documents/page.tsx:1` **med** · `page.tsx` · len=801
- `frontend/src/app/(app)/transactions/page.tsx:1` **med** · `page.tsx` · len=742
- `frontend/src/app/(app)/plano/page.tsx:1` **med** · `page.tsx` · len=630
- `frontend/src/app/(app)/plano/alocacao/wizard/page.tsx:1` **med** · `page.tsx` · len=533
- `frontend/src/app/(app)/dashboard/page.tsx:1` **med** · `page.tsx` · len=525

### T3_ts_long_functions

- `frontend/src/components/NotificationCenter.tsx:62` **high** · `NotificationCenter` · len=164
- `frontend/src/app/register/page.tsx:15` **high** · `RegisterPageInner` · len=130
- `frontend/src/components/CommandPalette.tsx:47` **high** · `CommandPalette` · len=111
- `frontend/src/app/login/page.tsx:15` **high** · `LoginPageInner` · len=108
- `frontend/src/components/tasks/UpcomingTasksWidget.tsx:29` **high** · `UpcomingTasksWidget` · len=94
- `frontend/src/components/report/sections/ApendiceASection.tsx:51` **high** · `ApendiceASection` · len=61
- `frontend/src/components/WorkspaceSwitcher.tsx:38` **high** · `WorkspaceSwitcher` · len=49
- `frontend/src/components/ConfirmDialog.tsx:60` **high** · `useConfirmDialog` · len=48
- `frontend/src/lib/useCurrentWorkspace.ts:32` **high** · `useCurrentWorkspace` · len=46
- `frontend/src/lib/pipelinePhases.ts:125` **high** · `computePhaseStates` · len=44

### T4_ts_forbidden_filename

- `frontend/src/lib/utils.ts:1` **med** · `utils.ts` · len=1

### T5_ts_hex_colors

- `frontend/src/app/(app)/dashboard/page.tsx:50` **med** · `#3b82f6` · len=1
- `frontend/src/app/(app)/dashboard/page.tsx:51` **med** · `#22c55e` · len=1
- `frontend/src/app/(app)/dashboard/page.tsx:52` **med** · `#ef4444` · len=1
- `frontend/src/app/(app)/dashboard/page.tsx:53` **med** · `#f59e0b` · len=1
- `frontend/src/app/(app)/dashboard/page.tsx:54` **med** · `#8b5cf6` · len=1
- `frontend/src/app/(app)/dashboard/page.tsx:55` **med** · `#06b6d4` · len=1
- `frontend/src/app/(app)/dashboard/page.tsx:56` **med** · `#ec4899` · len=1
- `frontend/src/app/(app)/dashboard/page.tsx:57` **med** · `#6366f1` · len=1
- `frontend/src/app/(app)/dashboard/page.tsx:58` **med** · `#14b8a6` · len=1
- `frontend/src/app/(app)/dashboard/page.tsx:59` **med** · `#f97316` · len=1

## Pivot por diretório

| Diretório | P1_long_functions | P2_long_files | P3_dict_str_any_boundary | P4_optional_no_default | P5_float_money | P6_forbidden_names | P7_multiparagraph_docstring | P8_what_comments | P9_deep_nesting | T1_ts_any | T2_ts_long_files | T3_ts_long_functions | T4_ts_forbidden_filename | T5_ts_hex_colors | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| backend/ | 328 | 8 | 7 | 4 | 13 | 2 | 315 | 5 | 42 | 0 | 0 | 0 | 0 | 0 | 724 |
| dev/ | 16 | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 12 | 0 | 0 | 0 | 0 | 0 | 40 |
| frontend/ | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 7 | 24 | 1 | 12 | 53 |
| pipeline/ | 135 | 3 | 64 | 0 | 47 | 0 | 226 | 0 | 50 | 0 | 0 | 0 | 0 | 0 | 525 |
| scripts/ | 225 | 15 | 0 | 0 | 7 | 0 | 108 | 53 | 120 | 0 | 0 | 0 | 0 | 0 | 528 |
| tests/ | 106 | 5 | 0 | 0 | 12 | 0 | 45 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 177 |
