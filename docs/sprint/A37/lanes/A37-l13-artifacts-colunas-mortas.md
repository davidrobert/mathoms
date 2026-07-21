---
id: A37.l13
type: lane
title: "pipeline_artifacts.schema_version e byte_size NULL em 100% das rows — popular ou dropar"
sprint: A37
status: planned
priority: P2
branch_slug: a37-l13-artifacts-colunas-mortas
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p2
  - area/dados
  - area/backend
---

# A37.l13 — `artifacts-colunas-mortas` (CTO-07)

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

`pipeline_artifacts.schema_version` e `byte_size` estão NULL em **10.191/10.191
rows** — as colunas nasceram na migration original da tabela (ADR-082, Fase 1)
e nunca foram ligadas: o write path (`DBArtifactStore.write` → `_insert`,
`backend/app/services/storage/db_artifact_store.py:412-430`) não as popula, e
a validação de schema em modo `warn` é log-only/efêmera — impossível auditar
por row qual schema validou, nem medir crescimento de storage por stage
(retention/FinOps).

## Escopo (decidir, depois executar)

- **Opção A (preferida):** popular no write path — `schema_version` a partir do
  schema resolvido em `SCHEMA_BY_STAGE`, `byte_size = len(payload serializado)`;
  considerar persistir o outcome da validação (ok/warn). Backfill das rows
  antigas é **opcional** (avaliar custo × valor com `data-engineer`; sem
  backfill, documentar a data de corte).
- **Opção B:** dropar as colunas via migration + ADR curta assumindo a decisão.
- Parecer do `data-engineer` **já colhido** (revisão do sprint, 2026-07-20):
  **Opção A** — `byte_size` é sinal load-bearing de retention/FinOps num store
  DB-only ([[ADR-212]]); ressalva: `schema_version` precisa ser **token real**
  (hash do schema ou `$id`+versão — os schemas hoje não declaram versão), senão
  vira constante sem valor de auditoria.

## Critério de aceite

- Opção A: teste de write → row nova tem `schema_version` e `byte_size`
  corretos; query de auditoria documentada no runbook.
- Opção B: migration + zero referência órfã no código; ADR mergeada.
- Em ambos: nenhuma coluna permanece "morta sem decisão registrada".

## Risco

Baixo (A) — só write path; migration (B) exige teste `pytest.mark.migration`.
