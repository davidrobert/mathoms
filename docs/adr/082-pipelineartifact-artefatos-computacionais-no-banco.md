---
id: ADR-082
type: adr
title: "PipelineArtifact: artefatos computacionais no banco"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 082"]
tags:
  - area/multitenancy
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 47
---

# ADR-082 — PipelineArtifact: artefatos computacionais no banco

**Status:** Decidido • **Data:** 2026-04-19 • **Status de execução:** [BACKLOG §Sprint A6](BACKLOG.md#sprint-a6--migração-infradomínio-plano-transversal)

**Contexto:** Artefatos intermediários do pipeline (E2–E7) viviam em
`storage/<ws>/processed/*.json` e o backend se referia a eles por convenção de
nome de arquivo (`_find_e2_extract`, `_e2_json_name`). Isso causava:

- Acoplamento frágil — renomear um arquivo quebra silenciosamente o backend.
- Modo incremental ambíguo — filtragem por stem matching permite dois E2 para o
  mesmo documento após reclassificação.
- Ausência de histórico auditável — sobrescrever é a única operação.
- Dificulta multi-tenant coerente — pastas por tenant mas linkage fora do DB.

**Decisão:** Nova tabela `pipeline_artifacts` como **fonte de verdade** para
artefatos computacionais do pipeline. Schema mínimo:

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | INTEGER PK | autoincrement |
| `workspace_id` | FK workspaces, NOT NULL, indexed | CASCADE |
| `pipeline_run_id` | FK pipeline_runs, NOT NULL, indexed | CASCADE |
| `stage` | VARCHAR(50) NOT NULL | `"E2"`... (Fases 1-8); `"reconcile_transactions"`... (pós-9) |
| `artifact_key` | VARCHAR(255) NOT NULL | stem do doc (E2) ou nome canônico (E3+) |
| `document_id` | FK documents, nullable | só E2-* (SET NULL no delete) |
| `content_json` | JSON NOT NULL | JSONB em Postgres |
| `schema_version`, `byte_size`, `created_at` | — | metadados |

Constraints: `UNIQUE(pipeline_run_id, stage, artifact_key)` + índices em
`(workspace_id, stage, artifact_key)` e `document_id`.

`document_id` é preenchido apenas em stages de extração (E2-*); `ON DELETE
SET NULL` preserva histórico do artefato mesmo se o documento for apagado.

**Consequências:**
- ✅ Elimina regex em nome de arquivo em `document_pipeline_sync.py` (Fase 3.2).
- ✅ Modo incremental determinístico via `Document.pipeline_last_run_at`.
- ✅ FK garante integridade referencial (antes: stored_path vs. stored_path estimado).
- ✅ Histórico auditável — cada run cria novos artefatos; runs anteriores permanecem.
- ⚠️ `content_json` em SQLite não é queryable por campo interno (aceitável hoje).
- ⚠️ Dados sensíveis em `content_json` — endereçado em ADR-095 (LGPD, fase futura).

**Arquivos:** `backend/app/models/pipeline_artifact.py`,
`backend/alembic/versions/p4q5r6s7t8u9_pipeline_artifacts.py`,
`backend/tests/test_pipeline_artifact_model.py`.
