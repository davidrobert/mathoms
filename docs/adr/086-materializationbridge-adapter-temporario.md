---
id: ADR-086
type: adr
title: "MaterializationBridge: adapter temporário"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 086"]
tags:
  - type/adr
  - status/decidido
size_lines: 42
---

# ADR-086 — MaterializationBridge: adapter temporário

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 2.2 / 9.6

**Contexto:** Migrar todos os scripts legados (48-108KB cada) para escrita
direta no `ArtifactStore` simultaneamente é inviável. Precisamos de um
mecanismo que permita ao orquestrador usar `DBArtifactStore` enquanto os
scripts ainda leem/escrevem em `processed/*.json`.

**Decisão:** `MaterializationBridge` context manager em
`pipeline/materialization_bridge.py`:

```python
with MaterializationBridge(store, pipeline_run_id=run_id) as bridge:
    root_dir = bridge.hydrate_for_stage("E3")   # DB → tmp/processed/E2_extracts/
    legacy_script(root_dir=root_dir)
    bridge.persist_from_stage("E3")             # tmp/processed/E3_reconciled/ → DB
```

- Hidratação consulta `StageSpec.reads` (sem lógica por stage hardcoded).
- Persistência consulta `StageSpec.writes`.
- Diretório efêmero `/tmp/fin_pipeline_{run_id}/` limpo no `__exit__` (mesmo
  em exception).
- Orquestrador detecta o tipo do store via helper
  `pipeline.stage_runner_compat.run_legacy_with_bridge_if_db`: `DiskArtifactStore`
  → roda com `root_dir=ctx.root`; outro store → bridge.

**Consequências:**
- ✅ Cutover stage-por-stage sem reescrever scripts pesados.
- ✅ Mesma bridge serve E3, E4, E5, E5.N, E7 — zero duplicação.
- ⚠️ I/O duplo (DB → disco → DB) em cada stage — overhead aceitável durante
  cutover; medido em Fase 1.4 (baseline).
- ❌ Temporário por contrato: removido na Fase 9.6 quando todos os stages
  estiverem no Caminho B. Guardrail: `grep -r MaterializationBridge` deve
  retornar zero antes da Fase 9.6.

**Arquivos:** `pipeline/materialization_bridge.py`,
`pipeline/stage_runner_compat.py`,
`tests/unit/pipeline/test_materialization_bridge.py`,
`tests/unit/pipeline/test_stage_runner_compat.py`.
