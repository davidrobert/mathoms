---
id: CHG-2026-04-15-F8-BUGS-OPERACIONAIS-CO
type: changelog-entry
date: "2026-04-15"
sprint: F8
summary: |
  Bugs operacionais corrigidos durante dogfood. - **parse_args() lendo `sys.argv` do Celery** — 6 scripts (e0_audit, e0_unlock, e0_route, e15_consolidate, e2_extract, e7_review) faziam `parser.parse_args()` q
tags:
  - type/changelog-entry
  - sprint/f8
---


# Bugs operacionais corrigidos durante dogfood


- **parse_args() lendo `sys.argv` do Celery** — 6 scripts (e0_audit, e0_unlock, e0_route, e15_consolidate, e2_extract, e7_review) faziam `parser.parse_args()` que dentro do Celery fork worker lia os argumentos do comando `celery` causando crash. Fix: `parse_args([] if root_dir else None)`.
- **SystemExit matando Celery worker** — scripts legados usam `sys.exit(1)` que em fork pool mata o processo inteiro. Fix: `_run_stage()` do orchestrator captura `SystemExit` → converte para `StageResult(success=False)`.
- **Stages dependentes de LLM não skipavam graciosamente** — E1.5c crasheava sem baseline (free tier), E7-apply crasheava sem review. Fix: ambos skippam graciosamente se dados ausentes.
- **Validação pré-pipeline + captura de stderr** — Pipeline dava "Script exited with code 1" genérico sem docs. Fix: validação pré-pipeline (HTTP 400) + captura de stdout/stderr no `_run_stage` com extração de linhas `[ERROR]`/`FATAL`.
- **Upload → classify → data/ roteamento** — 107 docs ficavam no `inbox/` sem chegar ao `data/`. Fix: `route_to_data_dir()` no document processor copia arquivo classificado de `inbox/` para `data/{dest_group}/`.
- **`_categorization` global missing no E4** — Scope issue. Fix: adicionar `_categorization` à declaração `global` do `_init_config`.
- **`skip_llm` default ignorava tier premium** — API sempre usava `DETERMINISTIC_ORDER`. Fix: `FULL_ORDER` quando `skip_llm=false`.
- **`FERNET_KEY` não persistida → secrets ilegíveis** — Nova key gerada a cada restart. Fix: persistir em `.env`.
- **`max_tokens=4096` insuficiente para E1.5** — LLM truncava. Fix: aumentado para 16384.
- **`started_at` sem timezone → "0s" elapsed** — SQLite salvava datetime naive → browser interpretava como hora local. Fix: `field_serializer` no Pydantic adiciona `tzinfo=UTC` antes de serializar.
- **Bolinha de running sem animação visual** — Fix: `animate-pulse` no ícone de stage em `running`.
