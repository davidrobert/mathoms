---
id: ADR-213
type: adr
title: "Sunset stage `audit_documents` (e cleanup de `_STAGE_TO_DIR` órfão)"
status: Decidido
phase: A12.sunset-audit
date: "2026-05-14"
relates_to:
  - "[[ADR-212]]"
  - "[[ADR-093]]"
  - "[[ADR-068]]"
supersedes: []
superseded_by: []
aliases: ["ADR 213", "sunset audit_documents"]
tags:
  - area/backend
  - area/pipeline
  - phase/a12
  - status/decidido
  - type/adr
---

## Contexto

[[ADR-212]] §Não-objetivos (item 2) preservou `scripts/e0_audit.py`
como **CLI read-only**, justificado por inspecionar filesystem
(detectar duplicatas + arquivos órfãos antes de qualquer pipeline
rodar). Premissa **incorreta** — descoberta em 2026-05-14 ao investigar
sufixos de naming a pedido do owner:

- `scripts/e0_audit.py` **não é CLI standalone**. É o stage `audit_documents`
  registrado em `FULL_ORDER` ([pipeline/stage_spec.py:181](../../pipeline/stage_spec.py)),
  com wrapper [pipeline/stages/audit_documents.py:13](../../pipeline/stages/audit_documents.py).
  Roda em todo `POST /pipeline/run`.

- 7 checks que cruzam:
  - `data/financial_statements/*` (filesystem ainda existe — upload area).
  - **`processed/E2_extracts/*-2_extract.json`** (filesystem; **NÃO EXISTE**
    em prod pós-[[ADR-212]] — artifacts vivem em `pipeline_artifacts` DB).
  - `inbox/` + `inbox_log.md`.

Em [`scripts/e0/audit_filename.py:25`](../../scripts/e0/audit_filename.py)
retorna `"E2_extracts/", "issue": "Diretório não existe", "severity": "ERROR"`
quando o diretório está ausente — situação normal pós-cutover.

**Consequência:** stage roda em prod gerando false-positives ou silencioso
(ninguém lê o output). Auditoria útil pré-pipeline está parcialmente
quebrada; produto não depende dela operacionalmente.

Cleanup adjacente: `_STAGE_TO_DIR` + `stage_dir_name()` em
[`pipeline/artifact_store.py`](../../pipeline/artifact_store.py)
**não têm caller de runtime** (verificado por `grep` em 2026-05-14):

- `pipeline/domain/services/e3_reconciler_adapter.py:239` usa só
  `stage_suffix` (não `stage_dir_name`).
- `pipeline/domain/services/e4_categorizer_adapter.py:194` idem.
- `pipeline/domain/services/e3_serialization.py` idem.
- `scripts/e0/audit_helpers.py` usa `_pc.E2_DIR` hard-coded, **não** o
  mapping.

Único consumidor real é o `test_mappings_have_same_keys` guardrail —
protege a sincronia entre dois mappings cuja metade (`_STAGE_TO_DIR`)
é dead code.

## Decisão

**Sunset do stage `audit_documents` + cleanup do mapping `_STAGE_TO_DIR`.**

### Stage `audit_documents`

1. Remover `"audit_documents"` de `FULL_ORDER` em `pipeline/stage_spec.py`.
2. Remover `STAGE_REGISTRY["audit_documents"]`.
3. Remover `"E0-audit": "audit_documents"` de `STAGE_RENAME_MAP` (rows
   históricas em `pipeline_artifacts` / `pipeline_stage_logs` com
   `stage="E0-audit"` ficam intocadas — são histórico de runs antigas;
   sem leitor reagindo, ficam órfãs sem efeito operacional).
4. Remover entry `"audit_documents"` do dispatcher em
   `pipeline/orchestrator.py`.
5. Deletar:
   - `pipeline/stages/audit_documents.py`
   - `scripts/e0_audit.py` (260 LoC)
   - `scripts/e0/__init__.py`
   - `scripts/e0/audit_filename.py`
   - `scripts/e0/audit_helpers.py`
   - `scripts/e0/audit_integrity.py`
   - `scripts/e0/audit_ledger.py`

### Mapping `_STAGE_TO_DIR`

1. Deletar `_STAGE_TO_DIR: dict[str, str]` (~25 LoC).
2. Deletar função `stage_dir_name(stage: str) -> str`.
3. Manter `_STAGE_TO_SUFFIX` + `stage_suffix()` — têm consumidores
   legítimos documentados em CLAUDE.md §"Convenções de naming de
   artefatos".

### Tests

1. `tests/unit/pipeline/test_artifact_stores.py` — remover:
   - Imports `_STAGE_TO_DIR`, `stage_dir_name`.
   - `TestStageMappings.test_mappings_have_same_keys`.
   - Asserts sobre `_STAGE_TO_DIR` em `test_resolvers_work_for_known_stages`,
     `test_resolvers_raise_for_unknown_stage`, `test_e1_members_mapping`,
     `test_legacy_e2_variants_all_present`.
2. `tests/test_stage_wrappers.py:64-67` — remover `test_import_audit_documents`.
3. `tests/unit/pipeline/test_stage_spec.py:38` — remover `"audit_documents"`
   do conjunto esperado em `FULL_ORDER`.
4. `tests/pipeline/perf/baseline_disk.json` — remover entry `"E0-audit": null`.
5. `backend/tests/fixtures/pipeline_runs.py` — remover fixture `("E0-audit", ...)`.
6. `backend/tests/test_retry_config.py:61` — remover `"E0-audit"` da lista
   iterada.

### Doc

1. CLAUDE.md §"Convenções de naming de artefatos" — atualizar bloco "5
   usos atuais do sufixo" removendo `scripts/e0_audit.py` (vai para 4
   usos).
2. ADRs históricas ([[ADR-068]], [[ADR-093]]) mantêm menções a "E0-audit"
   como referência histórica — não tocar (são notas atómicas com data
   fixa, são memória).

## Por que sunset (não refactor)

Trade-off considerado:
- **Refactor para DB** (~1-2d): reescrever `scripts/e0/audit_*.py` para
  consultar `pipeline_artifacts` em vez de `processed/E2_extracts/`.
  Adapta 7 checks. Resultado: stage funcional, mas baixo valor — produto
  não depende dele para correção.
- **Sunset** (~0.5d): -260 LoC + cleanup mapping. Replace nada;
  auditoria pré-pipeline some.

Sunset escolhido porque:
- **Custo de mantê-lo (refactorado) > benefício**. Gates equivalentes
  já existem em outros pontos:
  - Document upload faz dedup por content_hash ([[ADR-082]]).
  - `dev/check_pipeline_boundaries.py` valida invariantes de boundary.
  - Stages E0-route + E0-unlock fazem suas próprias validações de input.
  - `dev/validate_frontmatter.py`/`check_doc_*.py` cobrem docs.
- Pós-[[ADR-212]] o audit já não opera em prod (output silencioso ou
  WARN em logs ninguém lê). Refactor produziria stage que faria
  trabalho redundante.
- Manter código vivo que não tem caller real é débito que confunde
  agentes/devs futuros (caso ADR-212 §Não-objetivos item 2 era
  exatamente esse problema — preservei pensando que era CLI útil).

## Consequências

**Positivas:**

- ✅ ~290 LoC deletados (260 de `scripts/e0_*` + 30 de mapping órfão).
- ✅ `FULL_ORDER` simplificado: 17 → 16 stages.
- ✅ Pipeline runtime reduzido em ~0.5-2s por run (stage executava 7
  checks de filesystem inúteis).
- ✅ Falsos-positivos `"E2_extracts/ não existe"` somem dos logs.
- ✅ Guardrail test deixa de proteger dead code.

**Negativas:**

- ⚠️ Auditoria pré-pipeline some. Mitigação: gates equivalentes existem
  (content_hash dedup, validações por-stage, etc.). Se algum check do
  audit_documents identificar problema real **único**, abrir issue
  apontando o check específico — reativá-lo (em forma DB-aware) será
  decisão pontual com escopo medido.
- ⚠️ Rows históricas em `pipeline_artifacts` / `pipeline_stage_logs`
  com `stage="E0-audit"` ou `stage="audit_documents"` ficam órfãs.
  Sem leitor reagindo, sem efeito operacional. Cleanup futuro
  via `DELETE FROM pipeline_stage_logs WHERE stage IN
  ('E0-audit','audit_documents')` é housekeeping opcional.
- ⚠️ Frontend pode ter referência a "E0-audit" em [[ADR-068]] mapping
  de progress UI ("Preparando seus documentos" cluster). UI continuará
  funcionando — string de progresso simplesmente não dispara mais
  com esse código. Confirmar via teste manual no smoke.

**Riscos avaliados:**

| Risco | Mitigação |
|---|---|
| Algum workspace específico depende de check do audit | Pré-PR: revisar 7 checks, confirmar que cada um é redundante OU sem ação operacional. Output do audit nunca foi consumido por nenhum endpoint/UI. |
| Test que importa `audit_documents` quebra | Inventário completo no escopo do PR; 6 arquivos de test atualizados em escopo. |
| Frontend trava sem "E0-audit" no progress | UI lê de `pipeline_stage_logs.stage` — se row não vier, simplesmente não exibe. Smoke test confirmará. |

## Supersedure parcial

[[ADR-212]] §Não-objetivos item 2 ("Migrar `scripts/e0_audit.py` para
endpoint. Mantém valor como CLI.") fica **obsoleto** — premissa era
incorreta (script era stage, não CLI). Esta ADR substitui a decisão
parcial: em vez de migrar para endpoint ou manter como CLI, **deletar**
após inventário confirmar baixo valor.

## Referências

- [[ADR-212]] — Sunset MATHOMS_USE_DB_ARTIFACTS (parcialmente superseded; item 2 §Não-objetivos)
- [[ADR-093]] — Rename completo de identificadores de stage (mantém menções históricas a "E0-audit")
- [[ADR-068]] — Códigos internos do pipeline nunca vazam na UI (mantém menção histórica)
- [`pipeline/stage_spec.py`](../../pipeline/stage_spec.py) — `FULL_ORDER` antes/depois desta ADR
- [`scripts/e0_audit.py`](../../scripts/e0_audit.py) — arquivo a deletar
