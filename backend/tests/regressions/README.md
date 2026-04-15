# Anti-regression bank — F6.5E.8

Cada arquivo `test_bug_NNN_<slug>.py` aqui prova que **um bug histórico não voltou**. Convenções:

- **Nome do arquivo:** `test_bug_<numero_zero_padded>_<slug>.py` (ex: `test_bug_004_fallback_cpf_leak.py`).
- **Docstring obrigatória:** seção `# Bug` com sintoma original, `# Fix` com o que mudou, `# Por que falharia se revertido` com a assertion crítica.
- **Cada test falha SE o fix for revertido.** Não use asserts genéricos — escreva o caso exato que reproduz o bug original.
- Se o bug é frontend (ex: `animate-pulse` faltando), criar arquivo placeholder com `pytest.skip("frontend regression — coberto em frontend/tests/...")`.

## Catálogo

| Bug      | Origem            | Status do test | Arquivo |
|----------|-------------------|----------------|---------|
| BUG-001  | Celery worker     | ✅ direto      | `test_bug_001_celery_task_discovery.py` |
| BUG-002  | Celery sys.path   | ✅ direto      | `test_bug_002_celery_pipeline_module.py` |
| BUG-003  | Pipeline pending  | ✅ via on_failure | `test_bug_003_celery_on_failure_marks_failed.py` |
| BUG-004  | CPF leak fallback | ✅ direto      | `test_bug_004_fallback_cpf_leak.py` |
| BUG-005  | Vault sem nav     | 🎯 frontend    | placeholder |
| BUG-006  | Botão Revisar     | 🎯 frontend    | placeholder |
| BUG-007  | skip_llm tier     | ✅ direto      | `test_bug_007_skip_llm_respects_tier.py` |
| BUG-008  | Notif silencia    | 🎯 frontend    | placeholder |
| BUG-009  | Export CSV pag.   | ✅ via endpoint | `test_bug_009_csv_export_all_pages.py` |
| BUG-011  | Dead imports      | 🎯 frontend (lint) | placeholder |
| BUG-012  | deleteNotif sem UI| 🎯 frontend    | placeholder |
| BUG-014  | account label     | ✅ direto      | `test_bug_014_account_label_field.py` |
| BUG-015  | familia.sobrenome | ✅ JÁ no `test_serializers_round_trip.py` | (link) |
| OP-1     | parse_args sys.argv | ✅ direto    | `test_bug_op001_parse_args_celery.py` |
| OP-2     | SystemExit Celery | ✅ via orchestrator | `test_bug_op002_systemexit_in_celery.py` |
| OP-3     | LLM stages skip   | ✅ direto      | `test_bug_op003_llm_stages_skip_gracefully.py` |
| OP-4     | Pipeline validation | ✅ direto    | `test_bug_op004_pipeline_validation_pre.py` |
| OP-5     | route_to_data_dir | ✅ direto      | `test_bug_op005_route_to_data_dir.py` |
| OP-6     | _categorization global | ✅ direto | `test_bug_op006_categorization_global.py` |
| OP-7     | skip_llm default  | ✅ direto      | `test_bug_op007_skip_llm_default.py` |
| OP-8     | FERNET_KEY persist | ✅ direto     | `test_bug_op008_fernet_persistence.py` |
| OP-9     | max_tokens E1.5   | ✅ direto      | `test_bug_op009_max_tokens_e15.py` |
| OP-10    | started_at tz     | ✅ direto      | `test_bug_op010_started_at_tz_aware.py` |
| OP-11    | animate-pulse     | 🎯 frontend    | placeholder |

## Pre-existing failures detectados em Bootstrap (2026-04-15)

10 falhas em `test_pipeline_api`, `test_pipeline_phase5`, `test_pipeline_review`, `test_retry_config`, `test_pipeline_task` — **NÃO catalogadas aqui** porque ainda não foram triadas e fixadas. Quando o root cause for identificado, criar `test_bug_PRENNN_<slug>.py` aqui.

## Como contribuir

Quando detectar um bug em produção:
1. Reproduza com test em `backend/tests/regressions/test_bug_NNN_<slug>.py` que **falha**.
2. Aplique o fix no código de produto.
3. O test agora deve **passar**.
4. Atualize a tabela acima.
