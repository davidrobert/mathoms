---
id: ADR-083
type: adr
title: "ArtifactStore: abstração de I/O para artefatos"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 083"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 60
---

# ADR-083 — ArtifactStore: abstração de I/O para artefatos

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 1.2 / 2.1

> ⚠️ **Parcialmente superseded por [[ADR-212]]** (2026-05-14; banner
> adicionado no audit r6, 2026-07-03): `DiskArtifactStore`, o default disco
> de `get_artifact_store()` e a flag `MATHOMS_USE_DB_ARTIFACTS` citados
> abaixo **não existem mais** — pipeline é DB-only via `DBArtifactStore`.
> Permanecem válidos: o protocol `ArtifactStore`, `InMemoryArtifactStore`
> em testes e a boundary `pipeline/` ↔ DB. Detalhe: [[ADR-212]]
> §"Supersedure parcial: ADR-083 §Contexto".

**Contexto:** Com `pipeline_artifacts` como nova fonte de verdade (ADR-082),
stages precisam de uma API comum que:
- Funcione tanto em CLI dev (disco, sem DB) quanto em web (DB).
- Seja testável em isolamento, sem banco nem disco.
- Respeite a fronteira arquitetural: `pipeline/` não importa SQLAlchemy
  (garantido por `dev/check_pipeline_boundaries.py`).

**Decisão:** `ArtifactStore` como **Protocol** (`@runtime_checkable`) em
`pipeline/artifact_store.py` com três implementações:

| Classe | Localização | Uso |
|---|---|---|
| `DiskArtifactStore` | `pipeline/artifact_store.py` | CLI dev, backward compat com `processed/` |
| `InMemoryArtifactStore` | `pipeline/artifact_store.py` | **Obrigatória** em testes de domain services |
| `DBArtifactStore` | `backend/app/services/db_artifact_store.py` | Web/Celery — sessão injetada pelo chamador |

Interface segregada (ISP): `ReadableArtifactStore` (read/list/exists) é um
subset para clientes só-leitura.

API canônica:
```python
store.read(stage, key) -> dict | None
store.list_keys(stage) -> list[str]
store.exists(stage, key) -> bool
store.write(stage, key, data, *, document_id=None) -> None
store.delete(stage, key) -> None
store.delete_stage(stage) -> int
```

`DBArtifactStore.__init__(session, workspace_id, pipeline_run_id)` — sessão é
**injetada** pelo chamador (Celery task abre, passa, fecha). O store não cria
nem fecha sessão — evita sessões órfãs e garante que toda a run compartilha
uma transação.

`WorkspaceContext.get_artifact_store()` retorna `DiskArtifactStore` por
default; web/Celery injetam `DBArtifactStore` via `for_tenant(artifact_store=)`.

Mapeamentos compartilhados `_STAGE_TO_DIR` e `_STAGE_TO_SUFFIX` (em
`pipeline/artifact_store.py`) formalizam a convenção legada de `processed/`
e servem tanto o `DiskArtifactStore` quanto o `MaterializationBridge`
(ADR-086). Invariante: `set(_STAGE_TO_DIR) == set(_STAGE_TO_SUFFIX)`.

**Consequências:**
- ✅ Services de domínio (Fase 6-8) testáveis sem fixtures de arquivo.
- ✅ Cutover gradual — flag `MATHOMS_USE_DB_ARTIFACTS` escolhe o store.
- ✅ Boundary `pipeline/` ↔ `sqlalchemy` preservada (DBArtifactStore fora).
- ⚠️ Três impls duplicam shape da API — protocolo garante paridade via testes.

**Arquivos:** `pipeline/artifact_store.py`,
`backend/app/services/db_artifact_store.py`,
`backend/app/repositories/pipeline_artifact_repository.py`,
`tests/unit/pipeline/test_artifact_stores.py`,
`backend/tests/test_db_artifact_store.py`,
`backend/tests/test_pipeline_artifact_repository.py`.
