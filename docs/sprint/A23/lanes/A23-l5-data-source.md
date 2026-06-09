---
id: A23.l5
type: lane
title: "Data Lineage F1 — fonte plugável (data_source + SourceRef)"
sprint: A23
plan: PLAN-data-lineage
status: in_progress
priority: P0
branch_slug: dl-f1-data-source
adrs:
  - "[[ADR-278]]"
depends_on: []
parallel_with:
  - "[[A23.l4]]"
tags:
  - type/lane
  - sprint/a23
  - status/in-progress
  - priority/p0
  - area/data-lineage
  - area/backend
  - area/persistence
---

# A23.l5 — fonte plugável (`data_source` + `SourceRef`)

> **Plano:** [[PLAN-data-lineage]] · Onda 1 (F1, contrato aditivo) · **eixo central**.
> Conforma à [[ADR-278]] (Decidida); não reabre. Co-design `data-engineer` +
> `senior-cto` + `sre-devops` registrado em 2026-06-08.

## Objetivo

Tornar a **origem de um artefato plugável**: hoje é `document_id`; amanhã (Open
Finance) precisa ser plugável sem reescrever downstream. Introduz a tabela
`data_source` + coluna `pipeline_artifacts.data_source_id` + o tipo de domínio
`SourceRef` (mirror puro do registro DB).

## Escopo (contrato aditivo, NÃO consumido ainda — G1)

| Item | Onde | Status |
|---|---|---|
| `SourceRef` (`DocumentSource` \| `FeedSource`) | `pipeline/domain/ports/source.py` (NOVO dir `ports/`) | ✅ |
| tabela `data_source` (+ unique natural key, índice ws) | `backend/app/models/data_source.py` + migration | ✅ |
| coluna `pipeline_artifacts.data_source_id` (nullable, indexada) | model + migration `adr278datasource` | ✅ |
| backfill idempotente `kind='document'` (E2 com `document_id`) | migration (guard `as_sql`) | ✅ |
| testes migration + `SourceRef` unit + `DB_SCHEMA_REFERENCE` | — | ✅ |

## Decisões travadas (co-design)

- **`SourceRef` = `Literal["document","feed"]`** (ADR-278 §37 — **não** "open_finance"/
  "manual"; provider distingue dentro de `feed`). Flat frozen dataclasses + validação em
  `__post_init__` (padrão `suggestion.py`). Carrega **só chave natural**; `data_source_id`
  e `institution_code`/`external_account_ref` são do adapter DB (`backend/`).
- **`SourceAdapter` adiado** — Protocol sem implementador+consumidor é dead code
  (`senior-cto`). Nasce na lane com o primeiro produtor E2 (F2 / `dl-f1-extract-check`).
- **Sentinela `''` NOT NULL** em `institution_code`/`external_account_ref` — NULL quebra o
  unique no Postgres (`NULLS DISTINCT`); evita unique parcial/`COALESCE` (`data-engineer`).
- **Índice simples (não CONCURRENTLY)** na migration — precedente [[ADR-275]]/[[ADR-282]];
  recriação CONCURRENTLY em escala fica no runbook G-e (`sre-devops`).
- **FK `data_source_id → data_source.id ON DELETE SET NULL` DEFERIDO ao runbook.** A
  migration Alembic (testada em SQLite) entrega coluna + índice + backfill; o FK é DDL
  Postgres-específico (`NOT VALID` + `VALIDATE` em tabela de alto volume, `sre-devops`) e
  SQLite/Alembic não faz `ALTER ADD COLUMN` com FK sem `batch copy_from` (que arrisca a
  reflexão da tabela `pipeline_artifacts`). Integridade via app layer até o runbook materializar
  o FK. **Segue para `dl-f1-migration-runbook`.**

## Critério de aceite

- `test_adr278_data_source_migration` (upgrade cria tabela/coluna/índice; downgrade remove).
- `test_source_ref` (narrowing por `kind`, frozen, validação de chave natural).
- `test_alembic_guardrails` verde (drift model↔migration, idempotência, offline SQL, linear).
- Goldens E3/E4/E5 + view-model snapshot verdes **sem rebaseline** (coluna DB ≠ payload de
  artefato; G1). `dev/check_pipeline_boundaries.py` verde (`SourceRef` puro).
- `DB_SCHEMA_REFERENCE.md` regenerado.

## Não-escopo

- FK DB + recriação CONCURRENTLY do índice → `dl-f1-migration-runbook`.
- Emissão de `source_ref` no `content_json` do E2 → F2 (`dl-f1-extract-check`/de-leak).
- `SourceAdapter` Protocol + adapter DB concreto → lane com primeiro consumidor (F2/F3).

## Owner sugerido

`data-engineer` (schema/migration/backfill) + `senior-cto` (`SourceRef` port). Co-design
da decisão em [[ADR-278]].
