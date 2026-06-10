---
id: A25.l3
type: lane
title: "Data Lineage F5 — edge table artifact_lineage_edge + query reversa"
sprint: A25
plan: PLAN-data-lineage
status: open
priority: P0
branch_slug: dl-f5-reverso
adrs:
  - "[[ADR-279]]"
depends_on: []
parallel_with: ["[[A25.l1]]", "[[A25.l4]]", "[[A25.l5]]"]
tags:
  - type/lane
  - sprint/a25
  - status/open
  - priority/p0
  - area/data-lineage
  - area/backend
---

# A25.l3 — `dl-f5-reverso` (F5 · edge table + query reversa)

> **Plano:** [[PLAN-data-lineage]] · §Arquitetura D. Conforma à [[ADR-279]] (DDL +
> B6/B8); não reabre. **Independente** — abre já.

## Objetivo

Reverso do lineage: "quais números dependem da fonte X" via tabela derivada
`artifact_lineage_edge`, materializada a cada run bem-sucedido, retenção N=1 (B6).

## Decisões de co-design (data-engineer + senior-cto, 2026-06-10 — travadas)

1. **Materialização via hook pós-run em `_run_post_processing`**
   (`backend/app/tasks/pipeline_task.py`), ao lado de `_create_report_from_output` —
   NÃO stage no `FULL_ORDER` (stage sem artefato tensiona ADR-093; write SQL violaria
   o boundary `pipeline/** ∌ sqlalchemy`). Best-effort: falha do writer = warning,
   não aborta run. O nome `materialize_lineage` da ADR descreve a operação, não
   obriga um `StageSpec`.
2. **Boundary:** deriver PURO `pipeline/domain/services/lineage_edge_deriver.py`
   (`_lineage` inline → lista de dataclasses `LineageEdge`, zero SQLAlchemy) + writer
   `backend/app/services/lineage_edge_writer.py` (espelha o padrão `DBArtifactStore`).
3. **DDL/FKs:** `workspace_id` FK CASCADE · `run_id` FK CASCADE ·
   `source_document_id` FK SET NULL · `data_source_id` FK SET NULL (espelha
   [[ADR-278]]). Postgres-only (SQLite app-layer, padrão do runbook).
   Índices: `(workspace_id, source_document_id)` (query reversa) +
   **`(workspace_id, run_id)`** (load-bearing p/ o DELETE cross-run — não estava
   explícito na ADR). Índice `(workspace_id, rule_ref)` **DEFERIDO** ([[ADR-279]]
   difere o índice reverso por rule_ref com o MCP prod) — coluna sim, índice não.
4. **Semântica N=1:** `DELETE WHERE workspace_id=:ws AND run_id != :current` +
   INSERT na **mesma transação** (atomicidade: nunca estado com 0 edges). Run falho
   → writer não roda → edges do último run *bem-sucedido* permanecem. Rerun do mesmo
   run_id é idempotente.
5. **Escopo honesto da query reversa (teto documentado):** o `_lineage` inline hoje
   para em E5 (inputs intra-E5; E4/E3 não emitem `_lineage`). A cadeia field-level
   NÃO chega a `document_id` — o deriver complementa a folha com o
   `report_lineage.py` coarse (run → documentos consumidos) para popular
   `source_document_id`. A query reversa entrega **"agregados de decisão do run R
   que dependem dos documentos consumidos por R"** (nível run→doc), não
   field-level-até-o-documento-exato. Fechamento field-level real (E4 emitir
   `_lineage` com folha `SourceRef`) é follow-up explícito, fora desta lane.

## Anti-armadilha (do plano)

Edge table N=1 **não** é fonte de auditoria de citação do parecer — auditoria
histórica usa o `_lineage` inline do E5 daquele run (`pipeline_artifacts`).

## Critério de aceite

- Deriver puro: `check_pipeline_boundaries` verde; teste de derivação sobre golden
  canônico (edges determinísticas, sorted).
- Migration Postgres-only com `pytestmark = pytest.mark.migration`; `CREATE INDEX
  CONCURRENTLY` fora de transação (`autocommit_block`); nova fase no runbook
  `data_lineage_migrations.md` (a §D atual é placeholder de outra migração).
- `test_edge_retention_n1`: 2 runs → só edges do run 2; run falho preserva anteriores.
- `test_reverse_query_by_source_document`: run canônico retorna os agregados que
  dependem do doc X (no nível run→doc; teto documentado no teste).
- Hook best-effort em `_run_post_processing`; roda só em run bem-sucedido.

## Owner

Agente da lane; co-design `data-engineer` + `senior-cto` (2026-06-10).
