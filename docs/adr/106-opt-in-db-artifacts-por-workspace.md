---
id: ADR-106
type: adr
title: "Opt-in DB artifacts por workspace + DBArtifactStore no Celery task (A6b)"
status: Decidido
phase: "A6b"
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 106"]
tags:
  - area/multitenancy
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 49
---

# ADR-106 — Opt-in DB artifacts por workspace + DBArtifactStore no Celery task (A6b)

**Status:** Decidido (A6b) • **Data:** 2026-04-19

**Contexto:** Após A6a, todos os stages escrevem via `ArtifactStore` — mas o
pipeline web (`pipeline_task.py`) sempre criava um `DiskArtifactStore` via
`WorkspaceContext.for_tenant` (default). O flag global `MATHOMS_USE_DB_ARTIFACTS`
existia na config mas nunca era consultado pelo task. Ativar o modo DB globalmente
de uma vez é arriscado — prefere-se opt-in por workspace para piloto controlado.

**Decisão:**
1. **Coluna `workspaces.use_db_artifacts_override: bool | None`** (migration
   `r6s7t8u9v0w1`): `None` → global flag; `True` → força DB; `False` → força Disk.
2. **`pipeline_task.run_pipeline_task`**: antes de iniciar os stages, verifica
   `_resolve_use_db_artifacts(ws_id)` (workspace override > global flag). Se `True`,
   abre uma sessão longa (`SyncSessionLocal()`), cria `DBArtifactStore`, injeta em
   `ctx.artifact_store`. Sessão sofre `commit()` após cada stage com sucesso.
   `finally` fecha a sessão mesmo em caso de falha/pausa.
3. **`dev/compare_disk_vs_db.py`**: script operacional que compara artefatos em
   disco vs DB para um workspace + run. Gate ≥99% de paridade. Ignora `_meta`,
   `created_at`, `updated_at` (diferenças esperadas).

**Por que sessão longa no Celery task (e não uma por stage)?**
`DBArtifactStore.write` faz `flush()`, não `commit()`. O commit ocorre após cada
stage para persistir progressivamente — se o pipeline falhar no stage N, os
artefatos dos stages 1..N-1 já estão no DB. Uma sessão por stage criaria N
transações sem o benefício de leitura cross-stage (E3 lê artefatos do E2 que
foram escritos na mesma run).

**Discrepâncias esperadas entre disco e DB (não são bugs):**
- `_meta.confidence`, `_meta.notes` — presentes em E2-llm, sem equivalente no DB.
- `created_at` no DB vs timestamp no path do disco — ignorado pelo script.
- Ordem de listas JSON (transações, investimentos) — SQLite/Postgres não garante
  ordem de inserção nas queries sem `ORDER BY` explícito. E3→E7 são insensíveis
  à ordem; o compare script ignora ordem de listas de top-level.
- `byte_size`, `schema_version` no `pipeline_artifacts` — não têm equivalente
  em disco; ignorados na comparação.

**Consequências:**
- ✅ Ativação gradual: piloto por workspace sem impacto em outros.
- ✅ `_resolve_use_db_artifacts` é um ponto único de decisão — fácil de remover em A6c.
- ✅ Script de paridade operacional; gate ≥99% mensurável.
- ⚠️ Sessão longa no Celery worker: para pipelines com muitos stages, a sessão
  pode ficar aberta por minutos. Aceitável para SQLite (dev) e PostgreSQL com
  pool_size adequado.
- ⚠️ A6b.3 (validação em workspace real) ainda pendente — depende de teste humano
  com dataset real (A6-human.8).
