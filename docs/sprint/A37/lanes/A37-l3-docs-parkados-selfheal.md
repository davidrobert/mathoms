---
id: A37.l3
type: lane
title: "Docs parkados como `other` não se auto-corrigem: stored_path drift + gate de key env-only"
sprint: A37
status: planned
priority: P1
branch_slug: a37-l3-docs-parkados-selfheal
adrs: ["[[ADR-329]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p1
  - area/dados
  - area/backend
---

# A37.l3 — `docs-parkados-selfheal` (DE-03)

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

10 documentos do workspace dogfood estão `doc_type='other'`, `needs_review=1`,
`classification_confidence=0.0` com `llm_skipped_reason='missing_api_key'` —
classificados numa janela sem API key e **nunca recuperados**, apesar de o
self-heal existir ([[ADR-329]], `retry_parked_documents_sync`, chamado em
`backend/app/tasks/pipeline_task.py:1516` no início de run premium). Perdas
substantivas: 1 informe PJ (pdf), 1 CSV de exchange, 3 planilhas (os 5 jpg sem
OCR são não-suportados legítimos).

Duas quebras estruturais:

1. **stored_path drift (7/10 docs):** o arquivo foi movido de `inbox/` para
   `inbox_processed/<data>/` no filesystem, mas `documents.stored_path`
   continua `inbox/<nome>` → o retry retorna `no_file`
   (`backend/app/services/documents/document_reclassify_retry.py:49-50`)
   **para sempre**. O bulk reclassify também skipa silenciosamente
   (`document_reclassify_bulk_service.py:120-122`).
2. **Gate de key assimétrico:** o retry e a classificação leem a key **só de
   `os.environ`** (`document_classification.py:81-87`;
   `pipeline_task.py:1515`), enquanto o parecer prefere `llm_config` DB-backed
   (`pipeline/stages/parecer_planejador.py:48-58`). Worker sem a env var →
   gate falha silencioso enquanto os stages LLM funcionam.

## Escopo

- Retry/bulk resolvem o path atual (fallback para `inbox_processed/**/<nome>`)
  **ou** o move de arquivo passa a atualizar `stored_path` — decidir com
  `data-engineer` na implementação (preferir corrigir o write no move +
  migração one-shot dos paths existentes).
- Gate de key do retry alinhado ao padrão do parecer (env **ou** `llm_config`).
- Operacional (pós-merge): disparar reclassify no workspace dogfood e validar
  recuperação dos docs re-tentáveis.
- Telemetria: retry loga contadores (`retried/no_file/skipped`) para o gap não
  voltar a ser invisível.

## Critério de aceite

- Teste de regressão: doc com `stored_path` stale + arquivo em
  `inbox_processed/` → retry **reclassifica** (hoje: `no_file`).
- Teste: key presente só em `llm_config` (sem env) → retry roda LLM.
- KR-D: no dogfood, docs re-tentáveis saem de `other`/conf 0.0 após um run.

## Risco

Baixo. Migração de paths é one-shot e idempotente; reclassificação não deleta
dado (só re-tagueia + dispara E2 nos recuperados).
